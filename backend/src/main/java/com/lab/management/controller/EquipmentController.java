package com.lab.management.controller;

import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.lab.management.common.Result;
import com.lab.management.dto.EquipmentDTO;
import com.lab.management.dto.EquipmentVO;
import com.lab.management.entity.Equipment;
import com.lab.management.entity.Laboratory;
import com.lab.management.service.EquipmentService;
import com.lab.management.service.LaboratoryService;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.*;

/**
 * 设备控制器
 */
@Slf4j
@RestController
@RequestMapping("/equipment")
@RequiredArgsConstructor
public class EquipmentController {

    private final EquipmentService equipmentService;
    private final LaboratoryService laboratoryService;

    /**
     * 分页查询设备
     */
    @GetMapping("/page")
    public Result<Page<EquipmentVO>> page(
            @RequestParam(defaultValue = "1") Integer current,
            @RequestParam(defaultValue = "10") Integer size,
            @RequestParam(required = false) String name,
            @RequestParam(required = false) Long labId,
            @RequestParam(required = false) String category,
            @RequestParam(required = false) String status) {

        Page<Equipment> page = equipmentService.page(current, size, name, labId, category, status);
        
        // 转换为VO并填充实验室名称
        Page<EquipmentVO> voPage = new Page<>(page.getCurrent(), page.getSize(), page.getTotal());
        voPage.setRecords(page.getRecords().stream().map(equipment -> {
            EquipmentVO vo = EquipmentVO.from(equipment);
            if (equipment.getLabId() != null) {
                Laboratory laboratory = laboratoryService.getById(equipment.getLabId());
                if (laboratory != null) {
                    vo.setLaboratoryName(laboratory.getName());
                }
            }
            return vo;
        }).collect(java.util.stream.Collectors.toList()));
        
        return Result.success(voPage);
    }

    /**
     * 查询设备详情
     */
    @GetMapping("/{id}")
    public Result<Equipment> getById(@PathVariable Long id) {
        Equipment equipment = equipmentService.getById(id);
        if (equipment == null) {
            return Result.error("设备不存在");
        }
        return Result.success(equipment);
    }

    /**
     * 创建设备（仅管理员）
     */
    @PostMapping
    @PreAuthorize("hasRole('ADMIN')")
    public Result<Equipment> create(@Validated @RequestBody EquipmentDTO dto) {
        try {
            Equipment equipment = equipmentService.create(dto);
            return Result.success("创建成功", equipment);
        } catch (Exception e) {
            log.error("创建设备失败", e);
            return Result.error(e.getMessage());
        }
    }

    /**
     * 更新设备（仅管理员）
     */
    @PutMapping("/{id}")
    @PreAuthorize("hasRole('ADMIN')")
    public Result<Equipment> update(@PathVariable Long id,
            @Validated @RequestBody EquipmentDTO dto) {
        try {
            Equipment equipment = equipmentService.update(id, dto);
            return Result.success("更新成功", equipment);
        } catch (Exception e) {
            log.error("更新设备失败", e);
            return Result.error(e.getMessage());
        }
    }

    /**
     * 删除设备（仅管理员）
     */
    @DeleteMapping("/{id}")
    @PreAuthorize("hasRole('ADMIN')")
    public Result<String> delete(@PathVariable Long id) {
        try {
            equipmentService.delete(id);
            return Result.success("删除成功");
        } catch (Exception e) {
            log.error("删除设备失败", e);
            return Result.error(e.getMessage());
        }
    }

    /**
     * 更新设备状态（仅管理员）
     */
    @PutMapping("/{id}/status")
    @PreAuthorize("hasRole('ADMIN')")
    public Result<Equipment> updateStatus(@PathVariable Long id,
            @RequestParam String status) {
        try {
            Equipment equipment = equipmentService.updateStatus(id, status);
            return Result.success("状态更新成功", equipment);
        } catch (Exception e) {
            log.error("更新设备状态失败", e);
            return Result.error(e.getMessage());
        }
    }

    /**
     * 根据实验室ID查询设备
     */
    @GetMapping("/lab/{labId}")
    public Result<Page<Equipment>> getByLabId(
            @PathVariable Long labId,
            @RequestParam(defaultValue = "1") Integer current,
            @RequestParam(defaultValue = "10") Integer size) {

        Page<Equipment> page = equipmentService.getByLabId(labId, current, size);
        return Result.success(page);
    }

    /**
     * 获取可用设备列表
     */
    @GetMapping("/available")
    public Result<Page<Equipment>> getAvailableEquipment(
            @RequestParam(defaultValue = "1") Integer current,
            @RequestParam(defaultValue = "10") Integer size,
            @RequestParam(required = false) Long labId) {

        Page<Equipment> page = equipmentService.getAvailableEquipment(current, size, labId);
        return Result.success(page);
    }
}
