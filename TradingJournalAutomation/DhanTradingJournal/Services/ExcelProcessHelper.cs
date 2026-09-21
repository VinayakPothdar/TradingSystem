using System;
using System.Diagnostics;
using System.IO;
using System.Threading;

namespace DhanTradingJournal.Services;

public static class ExcelProcessHelper
{
    /// <summary>
    /// Checks whether the target Excel file is locked by another process (e.g. EXCEL.EXE).
    /// If locked, it terminates Excel processes to ensure uninterrupted read/write access.
    /// </summary>
    public static void EnsureFileAccessible(string filePath)
    {
        if (string.IsNullOrWhiteSpace(filePath) || !File.Exists(filePath))
            return;

        for (var attempt = 1; attempt <= 3; attempt++)
        {
            if (!IsFileLocked(filePath))
                return;

            Console.WriteLine($"[NOTICE] '{Path.GetFileName(filePath)}' is currently locked by Excel. Closing Excel to obtain read/write access (attempt {attempt}/3)...");
            KillExcelProcesses();
            Thread.Sleep(800);
        }
    }

    /// <summary>
    /// Tests if a file is exclusively locked by another process.
    /// </summary>
    public static bool IsFileLocked(string filePath)
    {
        if (!File.Exists(filePath)) return false;

        try
        {
            using var stream = new FileStream(filePath, FileMode.Open, FileAccess.ReadWrite, FileShare.None);
            return false;
        }
        catch (IOException)
        {
            return true;
        }
        catch (UnauthorizedAccessException)
        {
            return true;
        }
    }

    /// <summary>
    /// Terminates all running instances of EXCEL.EXE.
    /// </summary>
    public static void KillExcelProcesses()
    {
        try
        {
            var processes = Process.GetProcessesByName("EXCEL");
            foreach (var p in processes)
            {
                try
                {
                    p.Kill(true);
                    p.WaitForExit(3000);
                }
                catch
                {
                    // Process may have already exited
                }
            }
        }
        catch (Exception ex)
        {
            Console.WriteLine($"[WARNING] Could not terminate Excel process: {ex.Message}");
        }
    }
}
