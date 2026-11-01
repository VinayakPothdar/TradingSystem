using System;
using System.Diagnostics;
using System.IO;

namespace DhanTradingJournal.Services;

public class HistoricalDataSyncService
{
    private readonly string _scriptPath;
    private readonly string _pythonExe;

    public HistoricalDataSyncService()
    {
        // Locate python executable
        _pythonExe = FindPythonExecutable();

        // Locate sync_traded_and_indices.py
        _scriptPath = FindScriptPath();
    }

    /// <summary>
    /// Runs historical candle sync.
    /// Modes: "matched" (trades only), "indices" (all indices), "custom" (comma-separated), "all" (Nifty 500), "both" (indices + trades), "positional" (8-year 2018-present for 200 WEMA).
    /// </summary>
    public bool RunSync(string mode, string? customSymbols = null)
    {
        if (!File.Exists(_scriptPath))
        {
            Console.WriteLine($"[ERROR] Sync script not found at: {_scriptPath}");
            return false;
        }

        var args = $"\"{_scriptPath}\" --mode {mode}";
        if (!string.IsNullOrWhiteSpace(customSymbols))
        {
            args += $" --symbols \"{customSymbols}\"";
        }

        Console.WriteLine($"\nLaunching Historical Candle Sync ({mode.ToUpper()})...\n");

        var psi = new ProcessStartInfo
        {
            FileName = _pythonExe,
            Arguments = args,
            WorkingDirectory = Path.GetDirectoryName(_scriptPath)!,
            UseShellExecute = false,
            RedirectStandardOutput = false,
            RedirectStandardError = false
        };

        try
        {
            using var proc = Process.Start(psi);
            proc?.WaitForExit();
            return proc?.ExitCode == 0;
        }
        catch (Exception ex)
        {
            Console.WriteLine($"[ERROR] Failed to run sync script: {ex.Message}");
            return false;
        }
    }

    private static string FindPythonExecutable()
    {
        // Check Windows py launcher first
        try
        {
            using var proc = Process.Start(new ProcessStartInfo
            {
                FileName = "py",
                Arguments = "--version",
                UseShellExecute = false,
                RedirectStandardOutput = true,
                RedirectStandardError = true,
                CreateNoWindow = true
            });
            proc?.WaitForExit();
            if (proc?.ExitCode == 0) return "py";
        }
        catch { }

        // Check local python path
        var localPython = Path.Combine(
            Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),
            "Python", "pythoncore-3.14-64", "python.exe");
        if (File.Exists(localPython)) return localPython;

        return "python";
    }

    private static string FindScriptPath()
    {
        var baseDir = AppContext.BaseDirectory;
        var dir = new DirectoryInfo(baseDir);

        // Search upward for Tools/sync_traded_and_indices.py
        while (dir != null)
        {
            var candidate1 = Path.Combine(dir.FullName, "Tools", "sync_traded_and_indices.py");
            if (File.Exists(candidate1)) return candidate1;

            var candidate2 = Path.Combine(dir.FullName, "TradingJournalAutomation", "DhanTradingJournal", "Tools", "sync_traded_and_indices.py");
            if (File.Exists(candidate2)) return candidate2;

            dir = dir.Parent;
        }

        return Path.Combine(baseDir, "Tools", "sync_traded_and_indices.py");
    }
}
