package local.northstar.catalog;

import static org.junit.jupiter.api.Assertions.*;
import java.net.URI;
import java.net.http.*;
import java.nio.file.*;
import java.util.*;
import local.northstar.NorthstarApplication;
import org.flywaydb.core.Flyway;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.condition.EnabledIfEnvironmentVariable;
import org.springframework.boot.builder.SpringApplicationBuilder;
import org.springframework.jdbc.core.JdbcTemplate;
import tools.jackson.databind.JsonNode;
import tools.jackson.databind.json.JsonMapper;

@EnabledIfEnvironmentVariable(named="NORTHSTAR_DB_TEST",matches="1")
class MultiCourseIntegrationTest {
    private final JsonMapper json=JsonMapper.builder().build();
    private final HttpClient http=HttpClient.newHttpClient();
    private String base;
    private JdbcTemplate admin;

    @Test void realMultiLessonVersionsParagraphsPaginationAccessAndStartupProtection() throws Exception {
        assertEquals("northstar_phase01_test",System.getenv("DB_NAME"));
        assertNotEquals("3308",System.getenv("MYSQL_PORT"));
        String expected=Objects.requireNonNull(System.getenv("NORTHSTAR_EXPECTED_DB_UUID"));
        assertNotEquals("104d5d9d-cd3f-11f1-8da4-920f115cf5cb",expected);
        try(var app=new SpringApplicationBuilder(NorthstarApplication.class).run("--server.port=0")) {
            admin=new JdbcTemplate(app.getBean(Flyway.class).getConfiguration().getDataSource());
            assertEquals(expected,admin.queryForObject("SELECT @@server_uuid",String.class));
            base="http://127.0.0.1:"+app.getEnvironment().getRequiredProperty("local.server.port")+"/api/v1";
            var demoBefore=admin.queryForList("SELECT * FROM sentence WHERE lesson_id='demo-01' ORDER BY id");
            var historyBefore=admin.queryForList("SELECT * FROM command_receipt ORDER BY event_id");
            Object pointer=admin.queryForObject("SELECT current_version_id FROM lesson WHERE id='demo-01'",String.class);
            fixture("fixture-a",2,12); fixture("fixture-b",3,24);
            admin.update("INSERT INTO book(id,catalog_key,sequence_no,title,edition_label,availability,declared_lesson_count,metadata_source) VALUES ('fixture-book','test-original',5,'原创测试集合','test-v1','catalog_only',3,'self-authored isolated fixture')");
            for(int i=1;i<=3;i++) admin.update("INSERT INTO lesson(id,slug,kind,availability,book_id,sequence_no,display_number) VALUES (?,?, 'original_demo','draft','fixture-book',?,?)","directory-"+i,"directory-"+i,i,"测试 "+i);
            admin.update("INSERT INTO lesson(id,slug,kind,availability,book_id) VALUES ('directory-unknown','directory-unknown','original_demo','draft','fixture-book')");
            // A real, explicitly ordered readable book-bound course; it is never placed in the four textbook books.
            admin.update("UPDATE lesson SET book_id='fixture-book',sequence_no=7,display_number='A' WHERE id='fixture-a'");
            assertThrows(org.springframework.dao.DataAccessException.class,()->admin.update("UPDATE lesson SET sequence_no=1 WHERE id='fixture-a'"));
            assertThrows(org.springframework.dao.DataAccessException.class,()->admin.update("UPDATE lesson SET sequence_no=0 WHERE id='fixture-a'"));
            for(String id:List.of("fixture-a","fixture-b")) for(int version=1;version<=2;version++) {
                var lesson=get("/lessons/"+id+"?versionId="+id+"-v"+version,200);
                int count=id.equals("fixture-a")?12:24, paragraphs=id.equals("fixture-a")?2:3;
                assertEquals(count,lesson.path("sentences").size()); assertEquals(paragraphs,lesson.path("paragraphs").size());
                assertEquals(id+"-v"+version,lesson.path("versionId").asText());
                for(int n=0;n<count;n++) {
                    var sentence=lesson.path("sentences").get(n);
                    assertEquals(n+1,sentence.path("sequence").asInt());
                    assertTrue(sentence.path("paragraphId").asText().startsWith(id+"-v"+version+"-p"));
                    assertTrue(sentence.path("audio").path("uri").asText().contains(id+"-v"+version));
                }
                assertFalse(lesson.toString().contains("answerKey"));
            }
            assertEquals("fixture-a-v2",get("/lessons/fixture-a",200).path("versionId").asText());
            assertEquals(2,get("/lessons/fixture-a/versions",200).path("versions").size());
            assertEquals("VERSION_NOT_FOUND",get("/lessons/fixture-a?versionId=unknown",404).path("code").asText());
            assertEquals("VERSION_LESSON_MISMATCH",get("/lessons/fixture-a?versionId=fixture-b-v1",422).path("code").asText());
            get("/lessons/unknown",404);get("/lessons/directory-1",404);get("/books/unknown/lessons",404);
            get("/books/fixture-book/lessons?limit=0",400);get("/books/fixture-book/lessons?cursor=bad",400);
            var all=new ArrayList<String>();String cursor="";
            do {
                var page=get("/books/fixture-book/lessons?limit=2"+(cursor.isEmpty()?"":"&cursor="+cursor),200);
                for(var item:page.path("items"))all.add(item.path("id").asText());
                cursor=page.path("nextCursor").isNull()?"":page.path("nextCursor").asText();
            }while(!cursor.isEmpty());
            assertEquals(List.of("directory-1","directory-2","directory-3","fixture-a","directory-unknown"),all);
            var first=get("/books/fixture-book/lessons?limit=1",200).path("nextCursor").asText();
            get("/books/nce-book-1/lessons?cursor="+first,400);
            var catalog=get("/books",200);
            for(var book:catalog.path("books"))if(!book.path("id").asText().equals("fixture-book")) {
                assertEquals(0,book.path("actualLessonCount").asInt());assertEquals(0,book.path("availableLessonCount").asInt());
                assertEquals("catalog_only",book.path("availability").asText());
                assertEquals(0,get("/books/"+book.path("id").asText()+"/lessons",200).path("items").size());
            }
            assertTrue(catalog.path("standaloneLessons").valueStream().noneMatch(l->l.path("id").asText().equals("fixture-a")));
            assertTrue(catalog.path("standaloneLessons").valueStream().anyMatch(l->l.path("id").asText().equals("demo-01")));
            assertThrows(org.springframework.dao.DataAccessException.class,()->admin.update("UPDATE sentence SET paragraph_id='fixture-b-v1-p1' WHERE id='fixture-a-v1-s1'"));
            assertThrows(org.springframework.dao.DataAccessException.class,()->admin.update("UPDATE sentence SET audio_asset_id='fixture-b-v1-a1' WHERE id='fixture-a-v1-s1'"));
            assertThrows(org.springframework.dao.DataAccessException.class,()->admin.update("UPDATE lesson SET current_version_id='fixture-b-v1' WHERE id='fixture-a'"));
            String audio="/audio/fixture-a-v1-a1";
            assertEquals(200,send(audio,null).statusCode());assertEquals(206,send(audio,"bytes=0-31").statusCode());assertEquals(416,send(audio,"bytes=999999999-").statusCode());
            admin.update("UPDATE lesson SET availability='withdrawn' WHERE id='fixture-b'");
            get("/lessons/fixture-b",404);get("/lessons/fixture-b/versions",404);assertEquals(404,send("/audio/fixture-b-v1-a1",null).statusCode());
            admin.update("UPDATE lesson SET availability='available' WHERE id='fixture-b'");
            admin.update("UPDATE content_license SET review_status='pending_review' WHERE id='fixture-a-license'");
            get("/lessons/fixture-a",404);assertEquals(404,send(audio,null).statusCode());
            admin.update("UPDATE content_license SET review_status='confirmed' WHERE id='fixture-a-license'");
            String key=admin.queryForObject("SELECT storage_key FROM audio_asset WHERE id='fixture-a-v1-a1'",String.class);
            admin.update("UPDATE audio_asset SET storage_key='../../outside.mp3' WHERE id='fixture-a-v1-a1'");
            assertEquals(503,send(audio,null).statusCode());get("/lessons/fixture-a?versionId=fixture-a-v1",503);
            admin.update("UPDATE audio_asset SET storage_key=? WHERE id='fixture-a-v1-a1'",key);
            admin.update("UPDATE audio_asset SET sha256=? WHERE id='fixture-a-v1-a1'","0".repeat(64));assertEquals(503,send(audio,null).statusCode());
            admin.update("UPDATE audio_asset SET sha256=? WHERE id='fixture-a-v1-a1'",ContentPackage.sha256(Files.readAllBytes(Path.of(System.getenv("NORTHSTAR_TEST_AUDIO")))));
            assertThrows(IllegalStateException.class,()->app.getBean(ContentSeeder.class).initialize());
            app.getBean(ContentSeeder.class).seed();app.getBean(ContentSeeder.class).seed();
            assertEquals(pointer,admin.queryForObject("SELECT current_version_id FROM lesson WHERE id='demo-01'",String.class));
            assertEquals(demoBefore,admin.queryForList("SELECT * FROM sentence WHERE lesson_id='demo-01' ORDER BY id"));
            assertEquals(historyBefore,admin.queryForList("SELECT * FROM command_receipt ORDER BY event_id"));
            // An incomplete frozen Demo must fail rather than silently repairing or writing.
            var tx=new org.springframework.transaction.support.TransactionTemplate(new org.springframework.jdbc.datasource.DataSourceTransactionManager(app.getBean(Flyway.class).getConfiguration().getDataSource()));
            tx.executeWithoutResult(status->{
                admin.update("UPDATE lesson_version SET manifest_sha256=? WHERE id='demo-01-v1'","0".repeat(64));
                assertThrows(IllegalStateException.class,()->app.getBean(ContentSeeder.class).seed());status.setRollbackOnly();
            });
        }
    }

    private void fixture(String id,int paragraphs,int count)throws Exception {
        byte[] audio=Files.readAllBytes(Path.of(System.getenv("NORTHSTAR_TEST_AUDIO")));
        var license=json.createObjectNode().put("id",id+"-license").put("sourceType","original").put("sourceRef","self-authored test text and mathematical synthetic tone; not speech or textbook audio").put("reviewStatus","confirmed").put("rightsScope","isolated self-created functional test only");
        admin.update("INSERT INTO content_license(id,source_type,source_ref,review_status,details_json) VALUES (?,'original',?,'confirmed',?)",id+"-license",id+"-self-created-test",license.toString());
        admin.update("INSERT INTO lesson(id,slug,kind,availability) VALUES (?,?,'original_demo','available')",id,id);
        for(int v=1;v<=2;v++) {
            String version=id+"-v"+v;
            var payload=json.createObjectNode().put("id",id).put("versionId",version).put("title",id.equals("fixture-a")?"Original Test A":"Original Test B").put("version",v).put("explanationLabel","本地预置测试讲解").put("audioLabel","原创合成测试音 · 非朗读/非发音示范");payload.putArray("exercises");
            String hash=ContentPackage.sha256(payload.toString().getBytes(java.nio.charset.StandardCharsets.UTF_8));
            admin.update("INSERT INTO lesson_version(id,lesson_id,version_no,license_id,content_sha256,manifest_sha256,payload_json,publication_state,release_ready) VALUES (?,?,?,?,?,?,?,'published',TRUE)",version,id,v,id+"-license",hash,hash,payload.toString());
            for(int n=1;n<=paragraphs;n++) {
                String identity=java.util.UUID.randomUUID().toString();admin.update("INSERT INTO paragraph_identity(id,lesson_id,registry_key) VALUES (?,?,?)",identity,id,identity);
                admin.update("INSERT INTO paragraph(id,version_id,stable_key,sequence_no,lesson_id,identity_id) VALUES (?,?,?,?,?,?)",version+"-p"+n,version,"paragraph-"+n,n,id,identity);
            }
            for(int n=1;n<=count;n++) {
                String identity=java.util.UUID.randomUUID().toString();admin.update("INSERT INTO sentence_identity(id,lesson_id,registry_key) VALUES (?,?,?)",identity,id,identity);
                String asset=version+"-a"+n,key=id+"/version-"+v+"/sounds/utterance-"+n+".mp3";
                Path target=Path.of(System.getenv("NORTHSTAR_CONTENT_ROOT")).resolve(key);Files.createDirectories(target.getParent());Files.write(target,audio);
                admin.update("INSERT INTO audio_asset(id,lesson_version_id,license_id,source_kind,storage_key,mime_type,byte_size,duration_ms,sha256,status) VALUES (?,?,?,'original_tts',?,'audio/mpeg',?,2000,?,'ready')",asset,version,id+"-license",key,audio.length,ContentPackage.sha256(audio));
                admin.update("INSERT INTO sentence(id,lesson_id,lesson_version_id,stable_key,sequence_no,speaker,text,translation,explanation,focus,audio_asset_id,start_ms,end_ms,paragraph_id,identity_id) VALUES (?,?,?,?,?,'Tester',?,'原创测试句','本地预置讲解','test',?,0,2000,?,?)",version+"-s"+n,id,version,"line-"+n,n,"I place test card "+n+" beside the window in version "+v+".",asset,version+"-p"+((n-1)/(count/paragraphs)+1),identity);
            }
        }
        admin.update("UPDATE lesson SET current_version_id=? WHERE id=?",id+"-v2",id);
    }
    private JsonNode get(String path,int status)throws Exception {var r=send(path,null);assertEquals(status,r.statusCode(),path);return json.readTree(r.body());}
    private HttpResponse<byte[]> send(String path,String range)throws Exception {
        var r=HttpRequest.newBuilder(URI.create(base+path));if(range!=null)r.header("Range",range);
        return http.send(r.build(),HttpResponse.BodyHandlers.ofByteArray());
    }
}
