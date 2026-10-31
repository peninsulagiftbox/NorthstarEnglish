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
        if (exception instanceof org.springframework.dao.DataAccessException) {
            return problem(HttpStatus.SERVICE_UNAVAILABLE, "DATABASE_UNAVAILABLE", "数据库连接暂不可用，请检查本地服务。", request.getRequestURI());
        }
        if (exception instanceof org.springframework.web.ErrorResponse error) {
            HttpStatus status = HttpStatus.valueOf(error.getStatusCode().value());
            return problem(status, "HTTP_" + status.value(), "请求的路径、方法或参数不受支持。", request.getRequestURI());
        }
        return problem(HttpStatus.INTERNAL_SERVER_ERROR, "INTERNAL_ERROR", "本地服务发生错误，请检查日志后重试。", request.getRequestURI());
    }
}
