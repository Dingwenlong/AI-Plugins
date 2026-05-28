IF OBJECT_ID(N'[dbo].[DeviceBinding]', N'U') IS NULL
BEGIN
    CREATE TABLE [dbo].[DeviceBinding] (
        [UUID] nvarchar(50) NOT NULL,
        [DeviceName] nvarchar(50) NULL,
        [LastUsedIp] nvarchar(50) NULL,
        [createdby] nvarchar(50) NULL,
        [modifiedby] nvarchar(50) NULL,
        [createdts] datetime NOT NULL,
        [lastmodifiedts] datetime NOT NULL,
        [synctimestamp] datetime NOT NULL,
        [BINDINGTYPE] varchar(1) NOT NULL,
        [MIDTYPE] varchar(20) NULL,
        [FIDOFLAG] varchar(20) NULL,
        [FIDOTIMESTAMP] datetime NULL,
        [QKLOGTIMESTAMP] datetime NULL,
        [MIDREQSEQ] varchar(300) NULL,
        [FIDOQRID] varchar(300) NULL,
        [TotpSecret] varchar(300) NOT NULL
    );
END
