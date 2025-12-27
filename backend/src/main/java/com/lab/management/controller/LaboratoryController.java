package com.lab.management.controller;

import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.lab.management.common.Result;
import com.lab.management.dto.LaboratoryDTO;
import com.lab.management.dto.LaboratoryVO;
import com.lab.management.entity.Laboratory;
import com.lab.management.service.EquipmentService;
import com.lab.management.service.LaboratoryService;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.*;

/**
 * 实验室控制器
 */
@Slf4j
@RestController
@RequestMapping("/laboratory")
@RequiredArgsConstructor
public class LaboratoryController {

    private final LaboratoryService laboratoryService;
    private final EquipmentService equipmentService;

    /**
     * 分页查询实验室
     */
    @GetMapping("/page")
    public Result<Page<LaboratoryVO>> page(
            @RequestParam(defaultValue = "1") Integer current,
            @RequestParam(defaultValue = "10") Integer size,
            @RequestParam(required = false) String name,
            @RequestParam(required = false) String type,
            @RequestParam(required = false) String status) {

        Page<Laboratory> page = laboratoryService.page(current, size, name, type, status);
        
        // 转换为VO并填充设备数量
        Page<LaboratoryVO> voPage = new Page<>(page.getCurrent(), page.getSize(), page.getTotal());
        voPage.setRecords(page.getRecords().stream().map(lab -> {
            LaboratoryVO vo = LaboratoryVO.from(lab);
            // 查询该实验室的设备数量（只查询总数，不查询具体数据）
            Page<com.lab.management.entity.Equipment> equipmentPage = 
                equipmentService.page(1, 1, null, lab.getId(), null, null);
            vo.setEquipmentCount((int) equipmentPage.getTotal());
            return vo;
        }).collect(java.util.stream.Collectors.toList()));
        
        return Result.success(voPage);
    }

    /**
     * 查询实验室详情
     */
    @GetMapping("/{id}")
    public Result<Laboratory> getById(@PathVariable Long id) {
        Laboratory laboratory = laboratoryService.getById(id);
        if (laboratory == null) {
            return Result.error("实验室不存在");
        }
        return Result.success(laboratory);
    }

    /**
     * 创建实验室（仅管理员）
     */
    @PostMapping
    @PreAuthorize("hasRole('ADMIN')")
    public Result<Laboratory> create(@Validated @RequestBody LaboratoryDTO dto) {
        try {
            Laboratory laboratory = laboratoryService.create(dto);
            return Result.success("创建成功", laboratory);
        } catch (Exception e) {
            log.error("创建实验室失败", e);
            return Result.error(e.getMessage());
        }
    }

    /**
     * 更新实验室（仅管理员）
     */
    @PutMapping("/{id}")
    @PreAuthorize("hasRole('ADMIN')")
    public Result<Laboratory> update(@PathVariable Long id,
            @Validated @RequestBody LaboratoryDTO dto) {
        try {
            Laboratory laboratory = laboratoryService.update(id, dto);
            return Result.success("更新成功", laboratory);
        } catch (Exception e) {
            log.error("更新实验室失败", e);
            return Result.error(e.getMessage());
        }
    }

    /**
     * 删除实验室（仅管理员）
     */
    @DeleteMapping("/{id}")
    @PreAuthorize("hasRole('ADMIN')")
    public Result<String> delete(@PathVariable Long id) {
        try {
            laboratoryService.delete(id);
            return Result.success("删除成功");
        } catch (Exception e) {
            log.error("删除实验室失败", e);
            return Result.error(e.getMessage());
        }
    }

    /**
     * 更新实验室状态（仅管理员）
     */
    @PutMapping("/{id}/status")
    @PreAuthorize("hasRole('ADMIN')")
    public Result<Laboratory> updateStatus(@PathVariable Long id,
            @RequestParam String status) {
        try {
            Laboratory laboratory = laboratoryService.updateStatus(id, status);
            return Result.success("状态更新成功", laboratory);
        } catch (Exception e) {
            log.error("更新实验室状态失败", e);
            return Result.error(e.getMessage());
        }
    }

    /**
     * 获取可用实验室列表
     */
    @GetMapping("/available")
    public Result<Page<Laboratory>> getAvailableLabs(
            @RequestParam(defaultValue = "1") Integer current,
            @RequestParam(defaultValue = "10") Integer size) {

        Page<Laboratory> page = laboratoryService.getAvailableLabs(current, size);
        return Result.success(page);
    }
}
