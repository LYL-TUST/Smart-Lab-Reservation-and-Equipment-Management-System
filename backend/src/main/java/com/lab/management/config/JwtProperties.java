package com.lab.management.config;

import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.stereotype.Component;
import lombok.Data;

/**
 * JWT配置属性
 */
@Data
@Component
@ConfigurationProperties(prefix = "jwt")
public class JwtProperties {
    
    /**
     * 密钥
     */
    private String secret;
    
    /**
     * 过期时间（毫秒）
     */
    private Long expiration;
    
    /**
     * 请求头
     */
    private String header;
    
    /**
     * 令牌前缀
     */
    private String prefix;
}

