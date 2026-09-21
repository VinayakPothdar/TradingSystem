namespace DhanTradingJournal.Security;

public static class DhanCredentialProvider
{
    private const string ClientIdVariableName = "DHAN_CLIENT_ID";

    public static DhanCredentials GetCredentials()
    {
        var clientId =
            Environment.GetEnvironmentVariable(ClientIdVariableName) ??
            Environment.GetEnvironmentVariable(ClientIdVariableName, EnvironmentVariableTarget.User) ??
            string.Empty;

        if (string.IsNullOrWhiteSpace(clientId))
        {
            Console.WriteLine($"Missing {ClientIdVariableName} environment variable.");
            Console.WriteLine("Set it once in PowerShell:");
            Console.WriteLine($"[Environment]::SetEnvironmentVariable(\"{ClientIdVariableName}\", \"your-client-id\", \"User\")");
            return new DhanCredentials();
        }

        var accessToken = ReadSecret("Enter Dhan access token: ");

        if (string.IsNullOrWhiteSpace(accessToken))
        {
            Console.WriteLine("Missing Dhan access token.");
            return new DhanCredentials();
        }

        return new DhanCredentials
        {
            ClientId = clientId,
            AccessToken = accessToken
        };
    }

    private static string ReadSecret(string prompt)
    {
        Console.Write(prompt);

        if (Console.IsInputRedirected)
        {
            var line = Console.ReadLine()?.Trim() ?? string.Empty;
            return line;
        }

        var chars = new List<char>();

        while (true)
        {
            var key = Console.ReadKey(intercept: true);

            if (key.Key == ConsoleKey.Enter)
            {
                Console.WriteLine();
                return new string([.. chars]);
            }

            if (key.Key == ConsoleKey.Backspace)
            {
                if (chars.Count > 0)
                    chars.RemoveAt(chars.Count - 1);

                continue;
            }

            if (!char.IsControl(key.KeyChar))
                chars.Add(key.KeyChar);
        }
    }
}

