package local.northstar.knowledge;

import java.text.Normalizer;
import java.util.Objects;
import java.util.Set;
import org.springframework.http.HttpStatus;

/** Entry-point normalization; the concept key column uses utf8mb4_0900_bin, not the schema default. */
public final class KnowledgeConcepts {
    public static final Set<String> KINDS=Set.of("vocabulary","grammar","collocation","pattern");
    private KnowledgeConcepts() {}
    public static String canonicalKey(String raw) {
        if(raw==null) throw new Failure(422,"KNOWLEDGE_KEY_REQUIRED","知识词条不能为空。");
        String value=Normalizer.normalize(raw,Normalizer.Form.NFC);
        var folded=new StringBuilder(value.length());
        boolean pendingSpace=false;
        for(int i=0;i<value.length();) {
            int codePoint=value.codePointAt(i); i+=Character.charCount(codePoint);
            if(isFoldableWhitespace(codePoint)) {pendingSpace=true;continue;}
            if(pendingSpace && folded.length()>0) folded.append(' ');
            pendingSpace=false;
            folded.appendCodePoint(codePoint);
        }
        if(folded.isEmpty()) throw new Failure(422,"KNOWLEDGE_KEY_REQUIRED","知识词条规范化后不能为空。");
        if(folded.codePoints().count()>255) throw new Failure(422,"KNOWLEDGE_KEY_TOO_LONG","知识词条不能超过255个字符。");
        return folded.toString();
    }
    // Java \s and trim() miss NBSP-class spaces; the registration contract folds all legal Unicode whitespace.
    private static boolean isFoldableWhitespace(int codePoint) {
        return Character.isWhitespace(codePoint) || codePoint==0x00A0 || codePoint==0x2007 || codePoint==0x202F;
    }
    public static final class Failure extends RuntimeException {
        public final int status;public final String code;
        public Failure(int status,String code,String message){super(message);this.status=status;this.code=code;}
    }
}
