package local.northstar.catalog;

import com.networknt.schema.*;
import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.text.Normalizer;
import java.time.Instant;
import java.util.*;
import tools.jackson.databind.JsonNode;
import tools.jackson.databind.json.JsonMapper;

public final class CoreContent {
    static final JsonMapper JSON = JsonMapper.builder().enable(tools.jackson.core.StreamReadFeature.STRICT_DUPLICATE_DETECTION).build();
    static final long MAX_BYTES = 64L * 1024 * 1024;
    public record Issue(String code, String message, String path, String severity, String suggestion) {}
    public record Bundle(Path root, JsonNode content, JsonNode manifest, String rawHash,
                         String contentHash, String manifestHash) {}
    private final List<Issue> issues = new ArrayList<>();

    static Object canonical(Object value) {
        if (value instanceof JsonNode node) return canonical(JSON.convertValue(node, Object.class));
        if (value instanceof Map<?, ?> map) {
            var sorted = new TreeMap<String, Object>();
            map.forEach((key, child) -> sorted.put(key.toString(), canonical(child)));
            return sorted;
        }
        if (value instanceof List<?> list) return list.stream().map(CoreContent::canonical).toList();
        return value;
    }

    static byte[] bytes(Object value) {
        return JSON.writeValueAsString(canonical(value)).getBytes(StandardCharsets.UTF_8);
    }

    public static String hash(Object value) { return ContentPackage.sha256(bytes(value)); }

    public static String transcript(List<String> texts) {
        String text = texts.stream().map(part -> Normalizer.normalize(
            part.replace("\r\n", "\n").replace('\r', '\n'), Normalizer.Form.NFC)
            .replaceAll("^[ \t\n]+|[ \t\n]+$", "")).collect(java.util.stream.Collectors.joining("\n")) + "\n";
        return ContentPackage.sha256(text.getBytes(StandardCharsets.UTF_8));
    }

    static Path checked(Path root, String name) throws java.io.IOException {
        Path relative = Path.of(name);
        if (name.isBlank() || relative.isAbsolute() || name.contains("\\") || name.contains("%")
                || Arrays.asList(name.split("/")).contains("..")) throw new java.io.IOException("PATH_OUTSIDE_ROOT");
        Path path = root.resolve(relative).toRealPath();
        if (!path.startsWith(root.toRealPath()) || !Files.isRegularFile(path)
                || Files.size(path) > MAX_BYTES) throw new java.io.IOException("PATH_OUTSIDE_ROOT_OR_SIZE");
        return path;
    }

    public static Bundle load(Path root) throws java.io.IOException {
        byte[] raw = Files.readAllBytes(checked(root, "package.json"));
        byte[] manifest = Files.readAllBytes(checked(root, "manifest.json"));
        var node = JSON.readTree(raw);
        return new Bundle(root.toRealPath(), node, JSON.readTree(manifest), ContentPackage.sha256(raw),
            hash(node), ContentPackage.sha256(manifest));
    }

    private void require(boolean valid, String code, String path, String message) {
        if (!valid) issues.add(new Issue(code, message, path, "error", "修正源包或重新人工审校，生成新计划后重试。"));
    }

    public List<Issue> validate(Bundle bundle) {
        issues.clear();
        var schema = SchemaRegistry.withDefaultDialect(SpecificationVersion.DRAFT_2020_12)
            .getSchema(SchemaLocation.of("classpath:catalog/core-v1.schema.json"));
        for (var error : schema.validate(bundle.content(), context ->
                context.executionConfig(config -> config.formatAssertionsEnabled(true)))) {
            issues.add(new Issue("SCHEMA_INVALID", error.getMessage(), error.getInstanceLocation().toString(),
                "error", "按照 core-v1 Schema 修正字段。"));
        }
        if (!issues.isEmpty()) return List.copyOf(issues);
        var content = bundle.content();
        var manifest = bundle.manifest();
        require(content.path("lesson").path("title").asText().length() <= 255, "FIELD_LENGTH", "/lesson/title", "标题最多255字符。");
        if (!content.path("book").isNull()) {
            require(content.path("book").path("title").asText().length() <= 255
                && content.path("book").path("editionLabel").asText().length() <= 100, "FIELD_LENGTH", "/book", "册标题或版本标签超过数据库边界。");
        }
        require(manifest.path("packageId").equals(content.path("packageId")), "MANIFEST_ID", "/manifest/packageId", "包身份不匹配。");
        require(bundle.rawHash().equals(manifest.path("rawSha256").asText()), "PACKAGE_RAW_HASH", "/manifest/rawSha256", "原始 JSON 哈希不匹配。");
        require(bundle.contentHash().equals(manifest.path("contentSha256").asText()), "PACKAGE_CONTENT_HASH", "/manifest/contentSha256", "规范化内容哈希不匹配。");
        require("northstar.json.sorted.v1".equals(manifest.path("normalization").asText()), "HASH_ALGORITHM", "/manifest/normalization", "不支持的哈希算法。");
        var sources = unique(content.path("sources"), "id", "/sources");
        var paragraphs = unique(content.path("paragraphs"), "id", "/paragraphs");
        var sentences = unique(content.path("sentences"), "id", "/sentences");
        var assets = unique(content.path("audioAssets"), "id", "/audioAssets");
        var occurrences = unique(content.path("knowledge"), "occurrenceId", "/knowledge");
        var exercises = unique(content.path("exercises"), "id", "/exercises");
        unique(content.path("exerciseSets"), "id", "/exerciseSets");
        unique(content.path("paragraphs"), "stableKey", "/paragraphs");
        unique(content.path("sentences"), "stableKey", "/sentences");
        order(content.path("paragraphs"), "/paragraphs");
        order(content.path("sentences"), "/sentences");
        require(transcript(texts(content.path("sentences"))).equals(content.path("version").path("transcriptSha256").asText()),
            "TRANSCRIPT_HASH", "/version/transcriptSha256", "全课 transcript-v1 不一致。");
        for (int index = 0; index < content.path("sources").size(); index++) {
            var source = content.path("sources").get(index);
            String path = "/sources/" + index;
            require(source.path("sourceRef").asText().length() <= 255, "FIELD_LENGTH", path + "/sourceRef", "来源引用最多255字符。");
            require("confirmed".equals(source.path("reviewStatus").asText())
                && !source.path("reviewer").asText("").isBlank()
                && date(source.path("reviewedAt").asText())
                && !source.path("proofRef").asText("").isBlank(), "LICENSE_UNCONFIRMED", path, "来源使用权未经确认。");
            require(Set.of("local_test_only", "local_use", "redistribution").contains(source.path("rightsScope").asText()),
                "RIGHTS_SCOPE", path + "/rightsScope", "许可范围必须明确。");
            file(bundle.root(), source.path("sourceRef").asText(), source.path("sha256").asText(), -1, path);
            var inventory = manifest.path("sourceInventory").path(source.path("id").asText());
            require(inventory.isObject() && inventory.path("sha256").equals(source.path("sha256"))
                && inventory.path("originalFilename").isString() && inventory.path("byteSize").isIntegralNumber()
                && inventory.path("createdAt").isString() && date(inventory.path("createdAt").asText())
                && (!inventory.hasNonNull("reviewedAt") || date(inventory.path("reviewedAt").asText()))
                && (!inventory.hasNonNull("expiresAt") || date(inventory.path("expiresAt").asText()))
                && (inventory.hasNonNull("reviewedAt") || inventory.hasNonNull("expiresAt")),
                "SOURCE_INVENTORY", "/manifest/sourceInventory", "原始文件清单不完整。");
            try {
                Path original = checked(bundle.root(), source.path("sourceRef").asText());
                require(Files.size(original) == inventory.path("byteSize").asLong(-1)
                    && original.getFileName().toString().equals(inventory.path("originalFilename").asText()),
                    "SOURCE_INVENTORY", "/manifest/sourceInventory/" + source.path("id").asText(), "原始文件名或大小不匹配。");
            } catch (java.io.IOException error) {
                require(false, "SOURCE_INVENTORY", "/manifest/sourceInventory", "原始来源文件不可读。");
            }
            if (inventory.hasNonNull("expiresAt")) {
                require(future(inventory.path("expiresAt").asText()), "LICENSE_EXPIRED", path, "许可失效或日期非法。");
            }
        }
        String textLicense = content.path("version").path("licenseId").asText();
        license(sources, textLicense, "text", content.path("lesson").path("kind").asText().equals("licensed"), "/version/licenseId");
        var review = manifest.path("proofreading");
        require("confirmed".equals(review.path("status").asText()) && !review.path("reviewer").asText("").isBlank()
            && date(review.path("reviewedAt").asText()) && review.path("revision").asInt() > 0,
            "PROOFREADING_UNCONFIRMED", "/manifest/proofreading", "必须由人工确认校对版本。");
        require(review.path("rawTranscript").isString() && review.path("correctedTranscript").isString()
            && ContentPackage.sha256(review.path("correctedTranscript").asText().getBytes(StandardCharsets.UTF_8))
                .equals(review.path("correctedSha256").asText()), "PROOFREADING_HASH", "/manifest/proofreading", "校对正文哈希不匹配。");
        require(sources.containsKey(textLicense) && review.path("sourceSha256").equals(sources.get(textLicense).path("sha256")),
            "PROOFREADING_SOURCE", "/manifest/proofreading/sourceSha256", "校对来源不匹配。");
        require(transcript(List.of(review.path("correctedTranscript").asText())).equals(
            content.path("version").path("transcriptSha256").asText()), "PROOFREADING_CONTENT", "/manifest/proofreading", "校对文本与课文不一致。");
        int previousParagraph = 0;
        for (int index = 0; index < content.path("sentences").size(); index++) {
            var sentence = content.path("sentences").get(index);
            var paragraph = paragraphs.get(sentence.path("paragraphId").asText());
            String path = "/sentences/" + index;
            require(paragraph != null, "PARAGRAPH_REFERENCE", path + "/paragraphId", "段落不存在或属于外版。");
            if (paragraph != null) {
                require(paragraph.path("sequence").asInt() >= previousParagraph, "PARAGRAPH_ORDER", path, "段落阅读顺序倒退。");
                previousParagraph = paragraph.path("sequence").asInt();
            }
            require(assets.containsKey(sentence.path("audioAssetId").asText()), "AUDIO_REFERENCE", path + "/audioAssetId", "音频不属于本包。");
        }
        for (var paragraph : content.path("paragraphs")) {
            require(sources.values().stream().anyMatch(source -> source.path("sourceRef").equals(paragraph.path("sourceRef"))),
                "PARAGRAPH_SOURCE", "/paragraphs", "段落来源不在来源清单。");
        }
        for (int index = 0; index < content.path("audioAssets").size(); index++) {
            var asset = content.path("audioAssets").get(index);
            String path = "/audioAssets/" + index;
            license(sources, asset.path("licenseId").asText(), "audio",
                asset.path("sourceKind").asText().equals("licensed_audio"), path + "/licenseId");
            Path media = file(bundle.root(), asset.path("storageKey").asText(), asset.path("sha256").asText(), asset.path("byteSize").asLong(), path);
            long decoded = -1;
            if (media != null) {
                try { decoded = AudioProbe.duration(media, asset.path("sha256").asText()); }
                catch (Exception error) { require(false, "AUDIO_DECODE", path, "音频无法真实解码。"); }
                require(Math.abs(decoded - asset.path("durationMs").asLong()) <= 1, "AUDIO_DURATION", path + "/durationMs", "时长与实际解码不一致。");
            }
            var covered = new ArrayList<JsonNode>();
            for (var sentence : content.path("sentences"))
                if (sentence.path("audioAssetId").equals(asset.path("id"))) covered.add(sentence);
            var alignment = asset.path("alignment");
            require(alignment.path("method").asText().length() <= 128
                && alignment.path("reviewer").asText("").length() <= 128, "FIELD_LENGTH", path + "/alignment", "对齐工具或审核人最多128字符。");
            require(!covered.isEmpty() && JSON.valueToTree(covered.stream().map(sentence -> sentence.path("id").asText()).toList())
                .equals(alignment.path("sentenceIds")), "ALIGNMENT_SCOPE", path + "/alignment/sentenceIds", "音轨覆盖集合或顺序不匹配。");
            require(asset.path("sha256").equals(alignment.path("audioSha256")), "ALIGNMENT_AUDIO_HASH", path + "/alignment/audioSha256", "对齐音频哈希失效。");
            require(transcript(covered.stream().map(sentence -> sentence.path("text").asText()).toList())
                .equals(alignment.path("transcriptSha256").asText()), "ALIGNMENT_TRANSCRIPT_HASH", path + "/alignment/transcriptSha256", "对齐子集转录哈希失效。");
            require("verified".equals(alignment.path("status").asText()) && !alignment.path("reviewer").asText("").isBlank()
                && date(alignment.path("reviewedAt").asText()), "ALIGNMENT_UNVERIFIED", path + "/alignment", "音轨需要实际人工听查。");
            long previousEnd = 0;
            for (var sentence : covered) {
                long start = sentence.path("startMs").asLong(), end = sentence.path("endMs").asLong();
                require(start >= previousEnd && end > start && end <= decoded, "AUDIO_INTERVAL", "/sentences/" + (sentence.path("sequence").asInt() - 1),
                    "时间区间重叠、越界或顺序非法。");
                previousEnd = end;
            }
        }
        if (content.has("fullAudioAssetId"))
            require(assets.containsKey(content.path("fullAudioAssetId").asText()), "FULL_AUDIO_REFERENCE", "/fullAudioAssetId", "整课音频不存在。");
        var concepts = new HashMap<String, String>();
        for (var occurrence : content.path("knowledge")) {
            require(sentences.containsKey(occurrence.path("sentenceId").asText()), "KNOWLEDGE_SOURCE", "/knowledge", "知识出现必须来自本课句子。");
            String key = occurrence.path("canonicalKey").asText();
            try {
                require(local.northstar.knowledge.KnowledgeConcepts.canonicalKey(key).equals(key), "CANONICAL_KEY", "/knowledge", "概念词条未规范化。");
            } catch (local.northstar.knowledge.KnowledgeConcepts.Failure error) {
                require(false, "CANONICAL_KEY", "/knowledge", "概念词条为空或无效。");
            }
            String identity = hash(List.of(occurrence.path("kind"), occurrence.path("canonicalKey"), occurrence.path("senseKey")));
            String previous = concepts.putIfAbsent(occurrence.path("conceptId").asText(), identity);
            require(previous == null || previous.equals(identity), "CONCEPT_CONFLICT", "/knowledge", "同一概念身份对应不同义项。");
        }
        for (int index = 0; index < content.path("exercises").size(); index++) {
            var exercise = content.path("exercises").get(index);
            String path = "/exercises/" + index;
            for (var id : exercise.path("sentenceIds"))
                require(sentences.containsKey(id.asText()), "EXERCISE_SOURCE", path + "/sentenceIds", "题目来源句不属于本包。");
            for (var id : exercise.path("occurrenceIds")) {
                var occurrence = occurrences.get(id.asText());
                require(occurrence != null && contains(exercise.path("sentenceIds"), occurrence.path("sentenceId")),
                    "EXERCISE_KNOWLEDGE", path + "/occurrenceIds", "目标知识不来自题目来源句。");
            }
            if ("dictation".equals(exercise.path("kind").asText())) {
                require(exercise.path("sentenceIds").size() == 1 && exercise.path("options").isEmpty()
                    && exercise.path("answerKey").isNull(), "DICTATION_CONTRACT", path, "听写标准来自唯一原句。");
            } else {
                var options = unique(exercise.path("options"), "id", path + "/options");
                require(options.size() >= 2 && options.size() <= 8 && options.containsKey(exercise.path("answerKey").asText())
                    && !exercise.path("occurrenceIds").isEmpty(), "CHOICE_CONTRACT", path, "选择题必须有有效选项、答案及知识来源。");
                require(!exercise.path("explanation").asText().isBlank(), "EXPLANATION_REQUIRED", path + "/explanation", "选择题需要解释。");
            }
        }
        require(content.path("exerciseSets").size() <= 1, "SET_PROTOCOL_UNSUPPORTED", "/exerciseSets", "当前测验运行时每版只支持一个默认题集。");
        for (var set : content.path("exerciseSets")) {
            require(set.path("id").asText().length() <= 36 && "practice".equals(set.path("purpose").asText())
                && "quiz_choice_v1".equals(set.path("protocolVersion").asText()), "SET_PROTOCOL_UNSUPPORTED", "/exerciseSets",
                "当前运行时只支持 practice / quiz_choice_v1，题集 ID 最多36字符。");
            for (var id : set.path("exerciseIds")) {
                var exercise = exercises.get(id.asText());
                require(exercise != null && "quiz_choice".equals(exercise.path("kind").asText()),
                    "SET_EXERCISE", "/exerciseSets", "动态测验题集仅支持本版 quiz_choice。");
            }
        }
        return List.copyOf(issues);
    }

    private static boolean contains(JsonNode array, JsonNode value) {
        for (var entry : array) if (entry.equals(value)) return true;
        return false;
    }
    private static List<String> texts(JsonNode sentences) {
        var result = new ArrayList<String>();
        for (var sentence : sentences) result.add(sentence.path("text").asText());
        return result;
    }
    private static boolean date(String value) {
        try { Instant.parse(value); return true; } catch (RuntimeException error) { return false; }
    }
    private static boolean future(String value) {
        try { return Instant.parse(value).isAfter(Instant.now()); } catch (RuntimeException error) { return false; }
    }
    private Map<String, JsonNode> unique(JsonNode array, String field, String path) {
        var result = new LinkedHashMap<String, JsonNode>();
        int index = 0;
        for (var node : array) {
            require(result.putIfAbsent(node.path(field).asText(), node) == null, "DUPLICATE_ID", path + "/" + index + "/" + field, "身份重复。");
            index++;
        }
        return result;
    }
    private void order(JsonNode array, String path) {
        int expected = 0;
        for (var node : array) require(node.path("sequence").asInt() == ++expected, "SEQUENCE", path + "/" + (expected - 1) + "/sequence", "序号必须连续且按顺序排列。");
    }
    private void license(Map<String, JsonNode> sources, String id, String medium, boolean licensed, String path) {
        var source = sources.get(id);
        require(source != null && medium.equals(source.path("medium").asText())
            && (licensed ? "licensed" : "original").equals(source.path("sourceType").asText()), "LICENSE_REFERENCE", path, "来源介质或使用权类型不匹配。");
    }
    private Path file(Path root, String name, String sha, long size, String path) {
        try {
            Path file = checked(root, name);
            require(ContentPackage.sha256(Files.readAllBytes(file)).equals(sha) && (size < 0 || Files.size(file) == size),
                "FILE_HASH", path, "文件字节哈希或大小不匹配。");
            return file;
        } catch (Exception error) {
            require(false, "FILE_PATH", path, "文件不可读、越界或超出限制。");
            return null;
        }
    }
}
