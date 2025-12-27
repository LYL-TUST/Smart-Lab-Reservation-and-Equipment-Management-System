package com.lab.management.dto;

import lombok.Data;

/**
 * 冲突检测结果DTO
 */
@Data
public class ConflictResult {
    
    private Boolean hasConflict;
    
    private String message;
    
    private Object conflictData;
    
    public ConflictResult() {}
    
    public ConflictResult(Boolean hasConflict, String message) {
        this.hasConflict = hasConflict;
        this.message = message;
    }
    
    public ConflictResult(Boolean hasConflict, String message, Object conflictData) {
        this.hasConflict = hasConflict;
        this.message = message;
        this.conflictData = conflictData;
    }
    
    public static ConflictResult noConflict() {
        return new ConflictResult(false, "无冲突");
    }
    
    public static ConflictResult conflict(String message) {
        return new ConflictResult(true, message);
    }
    
    public static ConflictResult conflict(String message, Object data) {
        return new ConflictResult(true, message, data);
    }
}

