{ pkgs }: {
  deps = [
    pkgs.nodejs
    pkgs.python311
    pkgs.python311Packages.pip
    # ffmpeg нужен Whisper-клиенту для некоторых форматов аудио
    pkgs.ffmpeg
  ];
}
