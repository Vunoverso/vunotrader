#ifndef VUNO_BRIDGE_PATHS_MQH
#define VUNO_BRIDGE_PATHS_MQH

string SnapshotDirectory()
{
   return InpBridgeRoot + "\\in";
}


string CommonFilesDirectory()
{
   return TerminalInfoString(TERMINAL_COMMONDATA_PATH) + "\\Files";
}


string SnapshotAbsoluteDirectory()
{
   return CommonFilesDirectory() + "\\" + SnapshotDirectory();
}


string CommandDirectory()
{
   return InpBridgeRoot + "\\out";
}


string FeedbackDirectory()
{
   return InpBridgeRoot + "\\feedback";
}


string MetadataDirectory()
{
   return InpBridgeRoot + "\\metadata";
}


void EnsureBridgeFolders()
{
   FolderCreate(InpBridgeRoot, FILE_COMMON);
   FolderCreate(SnapshotDirectory(), FILE_COMMON);
   FolderCreate(CommandDirectory(), FILE_COMMON);
   FolderCreate(FeedbackDirectory(), FILE_COMMON);
   FolderCreate(MetadataDirectory(), FILE_COMMON);

   FolderCreate(InpBridgeRoot);
   FolderCreate(SnapshotDirectory());
   FolderCreate(CommandDirectory());
   FolderCreate(FeedbackDirectory());
   FolderCreate(MetadataDirectory());
}

#endif