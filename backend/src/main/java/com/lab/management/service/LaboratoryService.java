package com.lab.management.service;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.lab.management.dto.LaboratoryDTO;
import com.lab.management.entity.Laboratory;
import com.lab.management.enums.LabStatus;
import com.lab.management.mapper.LaboratoryMapper;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.BeanUtils;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.util.StringUtils;

/**
 * 实验室服务
 */
@Slf4j
@Service
@RequiredArgsConstructor
public class LaboratoryService {
    
    private final LaboratoryMapper laboratoryMapper;
    private final StateMachineService stateMachineService;
    
    /**
     * 分页查询实验室
     */
    public Page<Laboratory> page(Integer current, Integer size, String name, String type, String status) {
        log.info("分页查询实验室: current={}, size={}, name={}, type={}, status={}", 
            current, size, name, type, status);
        
        Page<Laboratory> page = new Page<>(current, size);
        LambdaQueryWrapper<Laboratory> wrapper = new LambdaQueryWrapper<>();
        
        if (StringUtils.hasText(name)) {
            wrapper.like(Laboratory::getName, name);
        }
        if (StringUtils.hasText(type)) {
            wrapper.eq(Laboratory::getType, type);
        }
        if (StringUtils.hasText(status)) {
            wrapper.eq(Laboratory::getStatus, status);
        }
        
        wrapper.orderByDesc(Laboratory::getCreatedAt);
        
        return laboratoryMapper.selectPage(page, wrapper);
    }
    
    /**
     * 根据ID查询实验室
     */
    public Laboratory getById(Long id) {
        log.info("查询实验室详情: id={}", id);
        return laboratoryMapper.selectById(id);
    }
    
    /**
     * 创建实验室
     */
    @Transactional(rollbackFor = Exception.class)
    public Laboratory create(LaboratoryDTO dto) {
        log.info("创建实验室: {}", dto.getName());
        
        Laboratory laboratory = new Laboratory();
        BeanUtils.copyProperties(dto, laboratory);
        
        // 设置默认状态
        if (!StringUtils.hasText(laboratory.getStatus())) {
            laboratory.setStatus(LabStatus.IDLE.name());
        }
        
        laboratoryMapper.insert(laboratory);
        log.info("实验室创建成功: id={}", laboratory.getId());
        
        return laboratory;
    }
    
    /**
     * 更新实验室
     */
    @Transactional(rollbackFor = Exception.class)
    public Laboratory update(Long id, LaboratoryDTO dto) {
        log.info("更新实验室: id={}", id);
        
        Laboratory laboratory = laboratoryMapper.selectById(id);
        if (laboratory == null) {
            throw new RuntimeException("实验室不存在");
        }
        
        BeanUtils.copyProperties(dto, laboratory);
        laboratory.setId(id);
        
        laboratoryMapper.updateById(laboratory);
        log.info("实验室更新成功: id={}", id);
        
        return laboratory;
    }
    
    /**
     * 删除实验室（逻辑删除）
     */
    @Transactional(rollbackFor = Exception.class)
    public void delete(Long id) {
        log.info("删除实验室: id={}", id);
        
        Laboratory laboratory = laboratoryMapper.selectById(id);
        if (laboratory == null) {
            throw new RuntimeException("实验室不存在");
        }
        
        laboratoryMapper.deleteById(id);
        log.info("实验室删除成功: id={}", id);
    }
    
    /**
     * 更新实验室状态
     */
    @Transactional(rollbackFor = Exception.class)
    public Laboratory updateStatus(Long id, String targetStatus) {
        log.info("更新实验室状态: id={}, targetStatus={}", id, targetStatus);
        
        Laboratory laboratory = laboratoryMapper.selectById(id);
        if (laboratory == null) {
            throw new RuntimeException("实验室不存在");
        }
        
        LabStatus currentStatus = LabStatus.valueOf(laboratory.getStatus());
        LabStatus newStatus = LabStatus.valueOf(targetStatus);
        
        // 验证状态转换
        if (!stateMachineService.validateLabStatusTransition(currentStatus, newStatus)) {
            String errorMsg = stateMachineService.getLabStatusTransitionErrorMessage(currentStatus, newStatus);
            throw new RuntimeException(errorMsg);
        }
        
        laboratory.setStatus(targetStatus);
        laboratoryMapper.updateById(laboratory);
        
        log.info("实验室状态更新成功: id={}, status={}", id, targetStatus);
        return laboratory;
    }
    
    /**
     * 获取所有可用实验室
     */
    public Page<Laboratory> getAvailableLabs(Integer current, Integer size) {
        log.info("查询可用实验室");
        
        Page<Laboratory> page = new Page<>(current, size);
        LambdaQueryWrapper<Laboratory> wrapper = new LambdaQueryWrapper<>();
        wrapper.in(Laboratory::getStatus, LabStatus.IDLE.name(), LabStatus.RESERVED.name())
               .orderByAsc(Laboratory::getName);
        
        return laboratoryMapper.selectPage(page, wrapper);
    }
}

