package local.northstar.config;

import java.io.IOException;
import java.util.Set;
import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import org.springframework.stereotype.Component;
import org.springframework.web.filter.OncePerRequestFilter;

@Component
public class LocalAccessFilter extends OncePerRequestFilter {
    private final Set<String> hosts;
    private final Set<String> origins;

    public LocalAccessFilter(LocalProperties properties) {
        hosts = Set.of("127.0.0.1:" + properties.apiPort(), "localhost:" + properties.apiPort(),
                "127.0.0.1:" + properties.webPort(), "localhost:" + properties.webPort());
        origins = Set.of("http://127.0.0.1:" + properties.webPort(), "http://localhost:" + properties.webPort());
    }

    @Override
    protected void doFilterInternal(HttpServletRequest request, HttpServletResponse response, FilterChain chain)
            throws ServletException, IOException {
        String origin = request.getHeader("Origin");
        String host = request.getHeader("Host");
        boolean loopbackHost = hosts.contains(host) || ("127.0.0.1:" + request.getLocalPort()).equals(host)
                || ("localhost:" + request.getLocalPort()).equals(host);
        if (!loopbackHost || (origin != null && !origins.contains(origin))) {
            response.setStatus(403);
            response.setContentType("application/problem+json");
            response.setCharacterEncoding("UTF-8");
            response.getWriter().write("{\"type\":\"urn:northstar:problem:local_access_only\",\"title\":\"Forbidden\",\"status\":403,\"code\":\"LOCAL_ACCESS_ONLY\",\"detail\":\"仅允许本地开发来源访问。\",\"instance\":\"/\",\"traceId\":\"" + java.util.UUID.randomUUID() + "\",\"retryable\":false,\"fieldErrors\":[]}");
            return;
        }
        response.setHeader("Cache-Control", "no-store");
        response.setHeader("X-Content-Type-Options", "nosniff");
        chain.doFilter(request, response);
    }
}
