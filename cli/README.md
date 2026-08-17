# Leverage CLI

The CLI is the simple command interface for Leverage. It is designed for the owner, not developers.

## Windows

From the repository folder:

```powershell
.\leverage.cmd help
```

Common commands:

```powershell
.\leverage.cmd status
.\leverage.cmd workers
.\leverage.cmd project list
.\leverage.cmd project status trading-toolkit
```

Create a new project:

```powershell
.\leverage.cmd project create --id my-project --name "My Project" --type saas
```

Prepare an owner payout. This does **not** transfer money:

```powershell
.\leverage.cmd payout prepare --project my-project --amount 100 --destination owner --purpose "profit withdrawal"
```

Approve a prepared payout. This records Boss approval but still does **not** transfer money while live money movement is disabled:

```powershell
.\leverage.cmd payout approve <payout-id>
```

The dashboard remains the visual command center. The CLI is the fast command path for routine checks and actions.
