//D:8003C580
ModelNode player_gait_hdr = {1, (union ModelRoData *)&player_gait_obj, 0, 0, 0, &player_gait_pos_hdr_1};
//D:8003C598
ModelNode player_gait_pos_hdr_1 = {2, (union ModelRoData *)&player_gait_pos_1, &player_gait_hdr, 0, 0, &player_gait_pos_hdr_2};
//D:8003C5B0
ModelNode player_gait_pos_hdr_2 = {2, (union ModelRoData *)&player_gait_pos_2, &player_gait_pos_hdr_1, 0, 0, &player_gait_pos_hdr_3};
//D:8003C5C8
ModelNode player_gait_pos_hdr_3 = {2, (union ModelRoData *)&player_gait_pos_3, &player_gait_pos_hdr_2, 0, 0, 0};
//D:8003C5E0
ModelRoData_HeaderRecord player_gait_obj = {
    .AnimPart = 0,
    .MatrixIndex = 1,
    .FirstGroupNode = &player_gait_pos_hdr_1,
    .Group1 = 0,
    .Group2 = 0,
    .RwDataIndex = 0,
    .reserved = 0,
};
//D:8003C5F0
ModelRoData_GroupRecord player_gait_pos_1 = {
    .Origin = {0.0, 0.0, 0.0},
    .JointID = 0x0001,
    .MatrixIDs = {0x0002, 0xFFFF, 0xFFFF},
    .ChildGroupNode = &player_gait_pos_hdr_2,
    .BoundingVolumeRadius = 0,
};
//D:8003C60C
ModelRoData_GroupRecord player_gait_pos_2 = {
    .Origin = {1.177982, 41.14437, 0.0},
    .JointID = 0x0002,
    .MatrixIDs = {0x0003, 0xFFFF, 0xFFFF},
    .ChildGroupNode = &player_gait_pos_hdr_3,
    .BoundingVolumeRadius = 0,
};
//D:8003C628
ModelRoData_GroupRecord player_gait_pos_3 = {
    .Origin = {-2.576027, 480.42902, 0.0},
    .JointID = 0x0003,
    .MatrixIDs = {0x0000, 0xFFFF, 0xFFFF},
    .ChildGroupNode = NULL,
    .BoundingVolumeRadius = 0,
};

//FIXME File split likely
//D:8003C644
s32 PAD_8003C644 = 0;
//D:8003C648
s32 PAD_8003C648 = 0;
//D:8003C64C
s32 PAD_8003C64C = 0;
