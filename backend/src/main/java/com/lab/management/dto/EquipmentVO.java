package com.lab.management.dto;

import com.lab.management.entity.Equipment;
import lombok.Data;
import lombok.EqualsAndHashCode;

/**
 * 设备视图对象
 */
@Data
@EqualsAndHashCode(callSuper = true)
public class EquipmentVO extends Equipment {
    private String laboratoryName;

    public static EquipmentVO from(Equipment equipment) {
        EquipmentVO vo = new EquipmentVO();
        // 复制所有属性
        vo.setId(equipment.getId());
        vo.setName(equipment.getName());
        vo.setModel(equipment.getModel());
        vo.setLabId(equipment.getLabId());
        vo.setCategory(equipment.getCategory());
        vo.setSerialNumber(equipment.getSerialNumber());
        vo.setStatus(equipment.getStatus());
        vo.setPurchaseDate(equipment.getPurchaseDate());
        vo.setPurchasePrice(equipment.getPurchasePrice());
        vo.setWarrantyPeriod(equipment.getWarrantyPeriod());
        vo.setDescription(equipment.getDescription());
        vo.setImageUrl(equipment.getImageUrl());
        vo.setCreatedAt(equipment.getCreatedAt());
        vo.setUpdatedAt(equipment.getUpdatedAt());
        vo.setDeleted(equipment.getDeleted());
        return vo;
    }
}

