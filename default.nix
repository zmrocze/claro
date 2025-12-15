{ symlinkJoin
, claro_app
, claro-notification
, claro-notification-scheduler
}:

# Combined derivation that includes the main Claro app and notification components
symlinkJoin {
  name = "claro-${claro_app.version}";
  
  paths = [
    claro_app
    claro-notification
    claro-notification-scheduler
  ];
  
  meta = claro_app.meta // {
    description = "Claro AI Assistant - Complete package with app and notifications";
    longDescription = ''
      Claro is a personal AI assistant with a chat interface and notifications.
      This package includes:
      - The main desktop application (claro)
      - Notification executable (claro-notification)
      - Notification scheduler (claro-notification-scheduler)
    '';
  };
}
