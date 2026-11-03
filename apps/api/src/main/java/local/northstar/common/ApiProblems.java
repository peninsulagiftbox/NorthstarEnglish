package local.northstar.common;

import java.net.URI;
import java.util.List;
import java.util.UUID;
import jakarta.servlet.http.HttpServletRequest;
import org.springframework.http.HttpStatus;
import org.springframework.http.ProblemDetail;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;

@RestControllerAdvice
public class ApiProblems {
    private static final org.slf4j.Logger log = org.slf4j.LoggerFactory.getLogger(ApiProblems.class);
    public static ProblemDetail problem(HttpStatus status, String code, String detail, String path) {
        var problem = ProblemDetail.forStatusAndDetail(status, detail);
        problem.setType(URI.create("urn:northstar:problem:" + code.toLowerCase(java.util.Locale.ROOT)));
        problem.setInstance(URI.create(path));
        problem.setProperty("code", code);
        problem.setProperty("traceId", UUID.randomUUID().toString());
        problem.setProperty("retryable", status == HttpStatus.SERVICE_UNAVAILABLE);
        problem.setProperty("fieldErrors", List.of());
        return problem;
    }

    @ExceptionHandler(Exception.class)
    ProblemDetail unexpected(Exception exception, HttpServletRequest request) {
        if (exception instanceof local.northstar.catalog.VersionAccess.Failure expected) {
            return problem(HttpStatus.valueOf(expected.status), expected.code, expected.getMessage(), request.getRequestURI());
        }
        if (exception instanceof org.springframework.web.server.ResponseStatusException expected) {
            return problem(HttpStatus.valueOf(expected.getStatusCode().value()), "PRACTICE_REQUEST", expected.getReason(), request.getRequestURI());
        }
        log.error("Unhandled exception at {}", request.getRequestURI(), exception);
        if (exception instanceof org.springframework.dao.DataAccessException db) {
            // Deadlocks, lock waits, timeouts and pooled-connection outages are transient; constraint,
            // grammar and mapping errors are deterministic and must not invite blind client retries.
            if (db instanceof org.springframework.dao.TransientDataAccessException
                || db instanceof org.springframework.dao.DataAccessResourceFailureException) {
                return problem(HttpStatus.SERVICE_UNAVAILABLE, "DATABASE_UNAVAILABLE", "数据库连接暂不可用，请检查本地服务。", request.getRequestURI());
            }
            if (db instanceof org.springframework.dao.DataIntegrityViolationException) {
                return problem(HttpStatus.INTERNAL_SERVER_ERROR, "DATA_CONFLICT", "请求与当前数据状态冲突，未产生变更；请检查请求内容或刷新后重试。", request.getRequestURI());
            }
            return problem(HttpStatus.INTERNAL_SERVER_ERROR, "INTERNAL_ERROR", "本地服务发生错误，请检查日志后重试。", request.getRequestURI());
        }
        if (exception instanceof org.springframework.web.ErrorResponse error) {
            HttpStatus status = HttpStatus.valueOf(error.getStatusCode().value());
            return problem(status, "HTTP_" + status.value(), "请求的路径、方法或参数不受支持。", request.getRequestURI());
        }
        return problem(HttpStatus.INTERNAL_SERVER_ERROR, "INTERNAL_ERROR", "本地服务发生错误，请检查日志后重试。", request.getRequestURI());
    }
}
