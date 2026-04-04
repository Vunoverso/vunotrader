#ifndef VUNO_BRIDGE_PATHS_MQH
#define VUNO_BRIDGE_PATHS_MQH

string SnapshotDirectory()
{
   return InpBridgeRoot + "\\in";
}


string CommandDirectory()
{
   return InpBridgeRoot + "\\out";
}


string FeedbackDirectory()
{
   return InpBridgeRoot + "\\feedback";
}


void EnsureBridgeFolders()
{
   FolderCreate(InpBridgeRoot, FILE_COMMON);
   FolderCreate(SnapshotDirectory(), FILE_COMMON);
   FolderCreate(CommandDirectory(), FILE_COMMON);
   FolderCreate(FeedbackDirectory(), FILE_COMMON);
}

#endif