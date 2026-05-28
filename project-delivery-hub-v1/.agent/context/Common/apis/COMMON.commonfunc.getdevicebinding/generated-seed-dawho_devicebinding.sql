IF NOT EXISTS (SELECT 1 FROM [dbo].[DeviceBinding] WHERE [UUID] = 'FIXTURE')
BEGIN
    INSERT INTO [dbo].[DeviceBinding] ([UUID], [DeviceName], [LastUsedIp], [createdby], [modifiedby], [createdts], [lastmodifiedts], [synctimestamp], [BINDINGTYPE], [MIDTYPE], [FIDOFLAG], [FIDOTIMESTAMP], [QKLOGTIMESTAMP], [MIDREQSEQ], [FIDOQRID], [TotpSecret])
    VALUES ('FIXTURE', 'FIXTURE', 'FIXTURE', 'FIXTURE', 'FIXTURE', '2026-04-15T10:00:00', '2026-04-15T10:00:00', '2026-04-15T10:00:00', 'FIXTURE', 'FIXTURE', 'FIXTURE', '2026-04-15T10:00:00', '2026-04-15T10:00:00', 'FIXTURE', 'FIXTURE', 'FIXTURE');
END
