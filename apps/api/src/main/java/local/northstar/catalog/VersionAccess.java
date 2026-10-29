package local.northstar.catalog;

import org.springframework.jdbc.core.JdbcOperations;
import org.springframework.transaction.support.TransactionSynchronizationManager;

/** Lock lesson then version in write transactions, in the same order as publication/withdrawal. */
public final class VersionAccess {
    private VersionAccess() {}
    public static void require(JdbcOperations db,String lesson,String version) {
        boolean transaction=TransactionSynchronizationManager.isActualTransactionActive();
        String lock=transaction?" FOR SHARE":"";
        var lessons=db.queryForList("SELECT availability FROM lesson WHERE id=?"+lock,lesson);
        var versions=db.queryForList("SELECT publication_state,license_id,release_ready FROM lesson_version WHERE id=? AND lesson_id=?"+lock,version,lesson);
        if(lessons.isEmpty() || versions.isEmpty())throw new Failure(422,"VERSION_LESSON_MISMATCH","课程与版本不匹配。");
        String state=versions.getFirst().get("publication_state").toString();
        if(state.equals("withdrawn"))throw new Failure(410,"VERSION_WITHDRAWN","此版本已撤回，不能开始新的学习操作。本机草稿和历史记录保留，请选择可用版本。");
        boolean legacy=lesson.equals("demo-01") && java.util.Set.of("demo-01-v1","demo-01-v2").contains(version);
        if(!legacy){
            var license=db.queryForList("SELECT review_status FROM content_license WHERE id=?"+lock,versions.getFirst().get("license_id"));
            if(!Boolean.TRUE.equals(versions.getFirst().get("release_ready")) || license.isEmpty() || !"confirmed".equals(license.getFirst().get("review_status")))throw new Failure(409,"CONTENT_RIGHTS_UNAVAILABLE","本版本来源或发布条件不可用；历史记录保留。");
        }
        if(!"available".equals(lessons.getFirst().get("availability")) || !state.equals("published"))throw new Failure(409,"VERSION_NOT_PUBLISHED","此版本尚未发布，不能开始学习。");
    }
    public static final class Failure extends RuntimeException {
        public final int status; public final String code;
        public Failure(int status,String code,String message){super(message);this.status=status;this.code=code;}
    }
}
