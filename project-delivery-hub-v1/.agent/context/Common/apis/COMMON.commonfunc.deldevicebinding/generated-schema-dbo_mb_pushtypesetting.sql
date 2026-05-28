IF OBJECT_ID(N'[DBO].[MB_PUSHTYPESETTING]', N'U') IS NULL
BEGIN
    CREATE TABLE [DBO].[MB_PUSHTYPESETTING] (
        [UserId] varchar(20) NULL,
        [DeviceId] varchar(100) NULL,
        [Type] char(1) NULL,
        [Active] bit NOT NULL,
        [CreateDate] datetime NOT NULL,
        [CreateUser] varchar(20) NULL,
        [ModifyDate] datetime NOT NULL,
        [ModifyUser] varchar(20) NULL
    );
END
