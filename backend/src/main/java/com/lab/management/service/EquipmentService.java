package com.lab.management.service;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.lab.management.dto.EquipmentDTO;
import com.lab.management.entity.Equipment;
import com.lab.management.enums.EquipmentStatus;
import com.lab.management.mapper.EquipmentMapper;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.BeanUtils;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.util.StringUtils;

/**
 * 设备服务
 */
@Slf4j
@Service
@RequiredArgsConstructor
public class EquipmentService {
    
    private final EquipmentMapper equipmentMapper;
    private final StateMachineService stateMachineService;
    
    /**
     * 分页查询设备
     */
    public Page<Equipment> page(Integer current, Integer size, String name, 
                                Long labId, String category, String status) {
        log.info("分页查询设备: current={}, size={}, name={}, labId={}, category={}, status={}", 
            current, size, name, labId, category, status);
        
        Page<Equipment> page = new Page<>(current, size);
        LambdaQueryWrapper<Equipment> wrapper = new LambdaQueryWrapper<>();
        
        if (StringUtils.hasText(name)) {
            wrapper.like(Equipment::getName, name);
        }
        if (labId != null) {
            wrapper.eq(Equipment::getLabId, labId);
        }
        if (StringUtils.hasText(category)) {
            wrapper.eq(Equipment::getCategory, category);
        }
        if (StringUtils.hasText(status)) {
            wrapper.eq(Equipment::getStatus, status);
        }
        
        wrapper.orderByDesc(Equipment::getCreatedAt);
        
        return equipmentMapper.selectPage(page, wrapper);
    }
    
    /**
     * 根据ID查询设备
     */
    public Equipment getById(Long id) {
        log.info("查询设备详情: id={}", id);
        return equipmentMapper.selectById(id);
    }
    
    /**
     * 创建设备
     */
    @Transactional(rollbackFor = Exception.class)
    public Equipment create(EquipmentDTO dto) {
        log.info("创建设备: {}", dto.getName());
        
        Equipment equipment = new Equipment();
        BeanUtils.copyProperties(dto, equipment);
        
        // 设置默认状态
        if (!StringUtils.hasText(equipment.getStatus())) {
            equipment.setStatus(EquipmentStatus.IDLE.name());
        }
        
        equipmentMapper.insert(equipment);
        log.info("设备创建成功: id={}", equipment.getId());
        
        return equipment;
    }
    
    /**
     * 更新设备
     */
    @Transactional(rollbackFor = Exception.class)
    public Equipment update(Long id, EquipmentDTO dto) {
        log.info("更新设备: id={}", id);
        
        Equipment equipment = equipmentMapper.selectById(id);
        if (equipment == null) {
            throw new RuntimeException("设备不存在");
        }
        
        BeanUtils.copyProperties(dto, equipment);
        equipment.setId(id);
        
        equipmentMapper.updateById(equipment);
        log.info("设备更新成功: id={}", id);
        
        return equipment;
    }
    
    /**
     * 删除设备（逻辑删除）
     */
    @Transactional(rollbackFor = Exception.class)
    public void delete(Long id) {
        log.info("删除设备: id={}", id);
        
        Equipment equipment = equipmentMapper.selectById(id);
        if (equipment == null) {
            throw new RuntimeException("设备不存在");
        }
        
        equipmentMapper.deleteById(id);
        log.info("设备删除成功: id={}", id);
    }
    
    /**
     * 更新设备状态
     */
    @Transactional(rollbackFor = Exception.class)
    public Equipment updateStatus(Long id, String targetStatus) {
        log.info("更新设备状态: id={}, targetStatus={}", id, targetStatus);
        
        Equipment equipment = equipmentMapper.selectById(id);
        if (equipment == null) {
            throw new RuntimeException("设备不存在");
        }
        
        EquipmentStatus currentStatus = EquipmentStatus.valueOf(equipment.getStatus());
        EquipmentStatus newStatus = EquipmentStatus.valueOf(targetStatus);
        
        // 验证状态转换
        if (!stateMachineService.validateEquipmentStatusTransition(currentStatus, newStatus)) {
            String errorMsg = stateMachineService.getEquipmentStatusTransitionErrorMessage(currentStatus, newStatus);
            throw new RuntimeException(errorMsg);
        }
        
        equipment.setStatus(targetStatus);
        equipmentMapper.updateById(equipment);
        
        log.info("设备状态更新成功: id={}, status={}", id, targetStatus);
        return equipment;
    }
    
    /**
     * 根据实验室ID查询设备列表
     */
    public Page<Equipment> getByLabId(Long labId, Integer current, Integer size) {
        log.info("查询实验室设备: labId={}", labId);
        
        Page<Equipment> page = new Page<>(current, size);
        LambdaQueryWrapper<Equipment> wrapper = new LambdaQueryWrapper<>();
        wrapper.eq(Equipment::getLabId, labId)
               .orderByAsc(Equipment::getName);
        
        return equipmentMapper.selectPage(page, wrapper);
    }
    
    /**
     * 获取可用设备列表
     */
    public Page<Equipment> getAvailableEquipment(Integer current, Integer size, Long labId) {
        log.info("查询可用设备: labId={}", labId);
        
        Page<Equipment> page = new Page<>(current, size);
        LambdaQueryWrapper<Equipment> wrapper = new LambdaQueryWrapper<>();
        wrapper.in(Equipment::getStatus, EquipmentStatus.IDLE.name(), EquipmentStatus.RESERVED.name());
        
        if (labId != null) {
            wrapper.eq(Equipment::getLabId, labId);
        }
        
        wrapper.orderByAsc(Equipment::getName);
        
        return equipmentMapper.selectPage(page, wrapper);
    }
}

