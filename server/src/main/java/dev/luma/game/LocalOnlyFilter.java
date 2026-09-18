package dev.luma.game;

import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import org.springframework.stereotype.Component;
import org.springframework.web.filter.OncePerRequestFilter;
import java.io.IOException;

/** Native loopback client only; do not permit arbitrary websites to trigger local POSTs. */
@Component
public class LocalOnlyFilter extends OncePerRequestFilter {
    @Override protected void doFilterInternal(HttpServletRequest request,HttpServletResponse response,FilterChain chain) throws ServletException,IOException {
        String host=request.getServerName();
        if(request.getHeader("Origin")!=null || !(host.equals("localhost")||host.equals("127.0.0.1")||host.equals("[::1]")||host.equals("::1"))) {
            response.sendError(403);return;
        }
        chain.doFilter(request,response);
    }
}
