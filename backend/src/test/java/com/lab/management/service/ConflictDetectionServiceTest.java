package com.lab.management.service;

import com.lab.management.dto.ConflictResult;
import com.lab.management.dto.ReservationDTO;
import com.lab.management.entity.Laboratory;
import com.lab.management.entity.MaintenanceRecord;
import com.lab.management.entity.Reservation;
import com.lab.management.enums.LabStatus;
import com.lab.management.mapper.LaboratoryMapper;
import com.lab.management.mapper.MaintenanceRecordMapper;
import com.lab.management.mapper.ReservationMapper;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.*;

/**
 * 冲突检测服务单元测试
 * 
 * 测试边界情况：
 * 1. 预约时间刚好衔接（不冲突）
 * 2. 预约时间完全重叠（冲突）
 * 3. 预约时间部分重叠（冲突）
 * 4. 跨天预约
 * 5. 同一用户多次预约
 * 6. 维护期间预约（应拒绝）
 * 7. 超出开放时间预约（应拒绝）
 * 8. 超过容量限制（应拒绝）
 */
@ExtendWith(MockitoExtension.class)
@DisplayName("冲突检测服务测试")
class ConflictDetectionServiceTest {

    @Mock
    private ReservationMapper reservationMapper;

    @Mock
    private LaboratoryMapper laboratoryMapper;

    @Mock
    private MaintenanceRecordMapper maintenanceRecordMapper;

    @InjectMocks
    private ConflictDetectionService conflictDetectionService;

    private Laboratory testLab;
    private ReservationDTO testDto;

    @BeforeEach
    void setUp() {
        // 初始化测试实验室
        testLab = new Laboratory();
        testLab.setId(1L);
        testLab.setName("测试实验室");
        testLab.setCapacity(50);
        testLab.setStatus(LabStatus.IDLE.name());

        // 初始化测试预约DTO
        testDto = new ReservationDTO();
        testDto.setLabId(1L);
        testDto.setStartTime(LocalDateTime.now().plusDays(1).withHour(9).withMinute(0));
        testDto.setEndTime(LocalDateTime.now().plusDays(1).withHour(11).withMinute(0));
        testDto.setParticipantCount(30);
    }

    @Test
    @DisplayName("测试1: 预约时间刚好衔接 - 不冲突")
    void testTimeConflict_ExactConnection_NoConflict() {
        // 已有预约: 9:00-11:00
        // 新预约: 11:00-13:00
        // 预期: 不冲突

        when(laboratoryMapper.selectById(1L)).thenReturn(testLab);
        when(reservationMapper.selectList(any())).thenReturn(new ArrayList<>());
        when(maintenanceRecordMapper.selectList(any())).thenReturn(new ArrayList<>());

        testDto.setStartTime(LocalDateTime.now().plusDays(1).withHour(11).withMinute(0));
        testDto.setEndTime(LocalDateTime.now().plusDays(1).withHour(13).withMinute(0));

        ConflictResult result = conflictDetectionService.detectConflict(testDto);

        assertFalse(result.getHasConflict(), "时间刚好衔接应该不冲突");
    }

    @Test
    @DisplayName("测试2: 预约时间完全重叠 - 冲突")
    void testTimeConflict_CompleteOverlap_Conflict() {
        // 已有预约: 9:00-11:00
        // 新预约: 9:00-11:00
        // 预期: 冲突

        Reservation existingReservation = new Reservation();
        existingReservation.setId(1L);
        existingReservation.setLabId(1L);
        existingReservation.setStartTime(testDto.getStartTime());
        existingReservation.setEndTime(testDto.getEndTime());
        existingReservation.setStatus("APPROVED");

        when(laboratoryMapper.selectById(1L)).thenReturn(testLab);
        when(reservationMapper.selectList(any())).thenReturn(Collections.singletonList(existingReservation));

        ConflictResult result = conflictDetectionService.detectConflict(testDto);

        assertTrue(result.getHasConflict(), "完全重叠应该冲突");
        assertTrue(result.getMessage().contains("时间冲突"));
    }

    @Test
    @DisplayName("测试3: 预约时间部分重叠 - 冲突（新预约开始时间在已有预约期间）")
    void testTimeConflict_PartialOverlap_StartInExisting_Conflict() {
        // 已有预约: 9:00-11:00
        // 新预约: 10:00-12:00
        // 预期: 冲突

        Reservation existingReservation = new Reservation();
        existingReservation.setId(1L);
        existingReservation.setLabId(1L);
        existingReservation.setStartTime(LocalDateTime.now().plusDays(1).withHour(9).withMinute(0));
        existingReservation.setEndTime(LocalDateTime.now().plusDays(1).withHour(11).withMinute(0));
        existingReservation.setStatus("APPROVED");

        testDto.setStartTime(LocalDateTime.now().plusDays(1).withHour(10).withMinute(0));
        testDto.setEndTime(LocalDateTime.now().plusDays(1).withHour(12).withMinute(0));

        when(laboratoryMapper.selectById(1L)).thenReturn(testLab);
        when(reservationMapper.selectList(any())).thenReturn(Collections.singletonList(existingReservation));

        ConflictResult result = conflictDetectionService.detectConflict(testDto);

        assertTrue(result.getHasConflict(), "部分重叠应该冲突");
    }

    @Test
    @DisplayName("测试4: 预约时间部分重叠 - 冲突（新预约结束时间在已有预约期间）")
    void testTimeConflict_PartialOverlap_EndInExisting_Conflict() {
        // 已有预约: 10:00-12:00
        // 新预约: 9:00-11:00
        // 预期: 冲突

        Reservation existingReservation = new Reservation();
        existingReservation.setId(1L);
        existingReservation.setLabId(1L);
        existingReservation.setStartTime(LocalDateTime.now().plusDays(1).withHour(10).withMinute(0));
        existingReservation.setEndTime(LocalDateTime.now().plusDays(1).withHour(12).withMinute(0));
        existingReservation.setStatus("APPROVED");

        testDto.setStartTime(LocalDateTime.now().plusDays(1).withHour(9).withMinute(0));
        testDto.setEndTime(LocalDateTime.now().plusDays(1).withHour(11).withMinute(0));

        when(laboratoryMapper.selectById(1L)).thenReturn(testLab);
        when(reservationMapper.selectList(any())).thenReturn(Collections.singletonList(existingReservation));

        ConflictResult result = conflictDetectionService.detectConflict(testDto);

        assertTrue(result.getHasConflict(), "部分重叠应该冲突");
    }

    @Test
    @DisplayName("测试5: 新预约完全包含已有预约 - 冲突")
    void testTimeConflict_NewContainsExisting_Conflict() {
        // 已有预约: 10:00-11:00
        // 新预约: 9:00-12:00
        // 预期: 冲突

        Reservation existingReservation = new Reservation();
        existingReservation.setId(1L);
        existingReservation.setLabId(1L);
        existingReservation.setStartTime(LocalDateTime.now().plusDays(1).withHour(10).withMinute(0));
        existingReservation.setEndTime(LocalDateTime.now().plusDays(1).withHour(11).withMinute(0));
        existingReservation.setStatus("APPROVED");

        testDto.setStartTime(LocalDateTime.now().plusDays(1).withHour(9).withMinute(0));
        testDto.setEndTime(LocalDateTime.now().plusDays(1).withHour(12).withMinute(0));

        when(laboratoryMapper.selectById(1L)).thenReturn(testLab);
        when(reservationMapper.selectList(any())).thenReturn(Collections.singletonList(existingReservation));

        ConflictResult result = conflictDetectionService.detectConflict(testDto);

        assertTrue(result.getHasConflict(), "新预约包含已有预约应该冲突");
    }

    @Test
    @DisplayName("测试6: 跨天预约")
    void testTimeConflict_CrossDay() {
        // 预约: 23:00 - 次日1:00

        testDto.setStartTime(LocalDateTime.now().plusDays(1).withHour(23).withMinute(0));
        testDto.setEndTime(LocalDateTime.now().plusDays(2).withHour(1).withMinute(0));

        when(laboratoryMapper.selectById(1L)).thenReturn(testLab);
        when(reservationMapper.selectList(any())).thenReturn(new ArrayList<>());
        when(maintenanceRecordMapper.selectList(any())).thenReturn(new ArrayList<>());

        ConflictResult result = conflictDetectionService.detectConflict(testDto);

        assertFalse(result.getHasConflict(), "跨天预约在无冲突情况下应该允许");
    }

    @Test
    @DisplayName("测试7: 维护期间预约 - 应拒绝")
    void testMaintenanceConflict_ShouldReject() {
        // 维护期间: 9:00-17:00
        // 新预约: 10:00-12:00
        // 预期: 冲突

        MaintenanceRecord maintenanceRecord = new MaintenanceRecord();
        maintenanceRecord.setId(1L);
        maintenanceRecord.setResourceType("LAB");
        maintenanceRecord.setResourceId(1L);
        maintenanceRecord.setStartTime(LocalDateTime.now().plusDays(1).withHour(9).withMinute(0));
        maintenanceRecord.setEndTime(LocalDateTime.now().plusDays(1).withHour(17).withMinute(0));
        maintenanceRecord.setStatus("IN_PROGRESS");

        when(laboratoryMapper.selectById(1L)).thenReturn(testLab);
        when(reservationMapper.selectList(any())).thenReturn(new ArrayList<>());
        when(maintenanceRecordMapper.selectList(any())).thenReturn(Collections.singletonList(maintenanceRecord));

        ConflictResult result = conflictDetectionService.detectConflict(testDto);

        assertTrue(result.getHasConflict(), "维护期间应该拒绝预约");
        assertTrue(result.getMessage().contains("维护"));
    }

    @Test
    @DisplayName("测试8: 超过容量限制 - 应拒绝")
    void testCapacityLimit_ShouldReject() {
        // 实验室容量: 50
        // 预约人数: 60
        // 预期: 拒绝

        testDto.setParticipantCount(60);

        when(laboratoryMapper.selectById(1L)).thenReturn(testLab);

        ConflictResult result = conflictDetectionService.detectConflict(testDto);

        assertTrue(result.getHasConflict(), "超过容量应该拒绝");
        assertTrue(result.getMessage().contains("容量"));
    }

    @Test
    @DisplayName("测试9: 实验室维护中状态 - 应拒绝")
    void testLabMaintenanceStatus_ShouldReject() {
        testLab.setStatus(LabStatus.MAINTENANCE.name());

        when(laboratoryMapper.selectById(1L)).thenReturn(testLab);

        ConflictResult result = conflictDetectionService.detectConflict(testDto);

        assertTrue(result.getHasConflict(), "实验室维护中应该拒绝预约");
        assertTrue(result.getMessage().contains("维护"));
    }

    @Test
    @DisplayName("测试10: 开始时间晚于结束时间 - 应拒绝")
    void testInvalidTimeRange_StartAfterEnd_ShouldReject() {
        testDto.setStartTime(LocalDateTime.now().plusDays(1).withHour(12).withMinute(0));
        testDto.setEndTime(LocalDateTime.now().plusDays(1).withHour(10).withMinute(0));

        ConflictResult result = conflictDetectionService.detectConflict(testDto);

        assertTrue(result.getHasConflict(), "开始时间晚于结束时间应该拒绝");
    }

    @Test
    @DisplayName("测试11: 开始时间早于当前时间 - 应拒绝")
    void testInvalidTimeRange_StartBeforeNow_ShouldReject() {
        testDto.setStartTime(LocalDateTime.now().minusHours(1));
        testDto.setEndTime(LocalDateTime.now().plusHours(1));

        ConflictResult result = conflictDetectionService.detectConflict(testDto);

        assertTrue(result.getHasConflict(), "开始时间早于当前时间应该拒绝");
    }

    @Test
    @DisplayName("测试12: 预约时长超过8小时 - 应拒绝")
    void testInvalidTimeRange_TooLong_ShouldReject() {
        testDto.setStartTime(LocalDateTime.now().plusDays(1).withHour(9).withMinute(0));
        testDto.setEndTime(LocalDateTime.now().plusDays(1).withHour(18).withMinute(0));

        ConflictResult result = conflictDetectionService.detectConflict(testDto);

        assertTrue(result.getHasConflict(), "预约时长超过8小时应该拒绝");
    }

    @Test
    @DisplayName("测试13: 实验室不存在 - 应拒绝")
    void testLabNotExists_ShouldReject() {
        when(laboratoryMapper.selectById(1L)).thenReturn(null);

        ConflictResult result = conflictDetectionService.detectConflict(testDto);

        assertTrue(result.getHasConflict(), "实验室不存在应该拒绝");
        assertTrue(result.getMessage().contains("不存在"));
    }

    @Test
    @DisplayName("测试14: 批量检测 - 部分冲突")
    void testBatchDetect_PartialConflict() {
        List<ReservationDTO> dtoList = new ArrayList<>();

        // 第一个预约 - 无冲突
        ReservationDTO dto1 = new ReservationDTO();
        dto1.setLabId(1L);
        dto1.setStartTime(LocalDateTime.now().plusDays(1).withHour(9).withMinute(0));
        dto1.setEndTime(LocalDateTime.now().plusDays(1).withHour(11).withMinute(0));
        dto1.setParticipantCount(30);
        dtoList.add(dto1);

        // 第二个预约 - 有冲突（超过容量）
        ReservationDTO dto2 = new ReservationDTO();
        dto2.setLabId(1L);
        dto2.setStartTime(LocalDateTime.now().plusDays(2).withHour(9).withMinute(0));
        dto2.setEndTime(LocalDateTime.now().plusDays(2).withHour(11).withMinute(0));
        dto2.setParticipantCount(60);
        dtoList.add(dto2);

        when(laboratoryMapper.selectById(1L)).thenReturn(testLab);
        when(reservationMapper.selectList(any())).thenReturn(new ArrayList<>());
        when(maintenanceRecordMapper.selectList(any())).thenReturn(new ArrayList<>());

        List<ConflictResult> results = conflictDetectionService.batchDetectConflict(dtoList);

        assertEquals(2, results.size());
        assertFalse(results.get(0).getHasConflict(), "第一个预约应该无冲突");
        assertTrue(results.get(1).getHasConflict(), "第二个预约应该有冲突");
    }

    @Test
    @DisplayName("测试15: 更新预约时排除自身")
    void testUpdateReservation_ExcludeSelf() {
        // 更新预约ID为1的预约，时间与自己重叠不应该算冲突

        Reservation existingReservation = new Reservation();
        existingReservation.setId(1L);
        existingReservation.setLabId(1L);
        existingReservation.setStartTime(testDto.getStartTime());
        existingReservation.setEndTime(testDto.getEndTime());
        existingReservation.setStatus("APPROVED");

        testDto.setId(1L); // 设置ID表示这是更新操作

        when(laboratoryMapper.selectById(1L)).thenReturn(testLab);
        when(reservationMapper.selectList(any())).thenReturn(new ArrayList<>()); // 排除自身后无冲突
        when(maintenanceRecordMapper.selectList(any())).thenReturn(new ArrayList<>());

        ConflictResult result = conflictDetectionService.detectConflict(testDto);

        assertFalse(result.getHasConflict(), "更新预约时应该排除自身");
    }
}
