package com.lab.management.common;

import lombok.Data;
import java.io.Serializable;
import java.util.List;

/**
 * 分页响应结果类
 */
@Data
public class PageResult<T> implements Serializable {
    
    private static final long serialVersionUID = 1L;
    
    private Long total;
    private List<T> records;
    private Long current;
    private Long size;
    
    public PageResult() {}
    
    public PageResult(Long total, List<T> records, Long current, Long size) {
        this.total = total;
        this.records = records;
        this.current = current;
        this.size = size;
    }
}

