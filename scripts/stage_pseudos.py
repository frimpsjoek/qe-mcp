"""
stage_pseudos.py — One-time setup: transfer SG15 pseudopotentials from your
Mac to Polaris via Globus Transfer.

Run once:
    python scripts/stage_pseudos.py

After this, set in claude_desktop_config.json:
    "QE_POLARIS_PSEUDO": "/home/<you>/sg15_oncv"
    "QE_POLARIS_ENDPOINT": "<polaris-filesystem-endpoint-uuid>"
"""

import os
import time
from pathlib import Path

# ── Configuration ─────────────────────────────────────────────────────────────

# Your local SG15 pseudopotential directory
LOCAL_PSEUDO_DIR = Path(__file__).parent.parent / "pseudopotentials" / "sg15_oncv"

# Polaris Globus Transfer endpoint (filesystem, NOT Globus Compute endpoint)
# Find it at https://app.globus.org → search "ALCF Polaris"
# Common value: 55fdf1d2-c57b-4a6a-8c0b-e33f64d9aece  (verify with ALCF docs)
POLARIS_ENDPOINT = os.environ.get(
    "QE_POLARIS_ENDPOINT",
    "55fdf1d2-c57b-4a6a-8c0b-e33f64d9aece",   # ALCF Polaris filesystem
)

# Where to stage the pseudos on Polaris
POLARIS_DEST = os.environ.get(
    "QE_POLARIS_PSEUDO",
    "/home/" + os.environ.get("USER", "user") + "/sg15_oncv",
)

# Your local Globus Connect Personal endpoint UUID
# Install Globus Connect Personal at https://www.globus.org/globus-connect-personal
# Then find your endpoint UUID in the Globus web app or with:
#   globus endpoint local-id
LOCAL_ENDPOINT = os.environ.get("QE_LOCAL_ENDPOINT", "")

# ── Transfer ──────────────────────────────────────────────────────────────────


def main():
    try:
        import globus_sdk
    except ImportError:
        print("globus-sdk not installed. Run: pip install globus-sdk")
        return

    # --- Auth ---
    # Use a Native App flow so we can get Transfer scope
    CLIENT_ID = "4cf29807-cf21-49ec-9443-ff9a3fb9f81c"  # Globus Compute client

    auth_client = globus_sdk.NativeAppAuthClient(CLIENT_ID)
    auth_client.oauth2_start_flow(
        requested_scopes=[
            globus_sdk.TransferClient.scopes.all,
        ],
        redirect_uri="https://auth.globus.org/v2/web/auth-code",
    )

    print("\nAuthenticate with Globus for Transfer:")
    print("--------------------------------------")
    print(auth_client.oauth2_get_authorize_url())
    code = input("\nPaste the auth code: ").strip()

    tokens = auth_client.oauth2_exchange_code_for_tokens(code)
    transfer_token = tokens.by_resource_server["transfer.api.globus.org"]["access_token"]
    authorizer = globus_sdk.AccessTokenAuthorizer(transfer_token)
    tc = globus_sdk.TransferClient(authorizer=authorizer)

    # --- Resolve local endpoint ---
    if not LOCAL_ENDPOINT:
        try:
            import subprocess
            result = subprocess.run(
                ["globus", "endpoint", "local-id"],
                capture_output=True, text=True
            )
            local_ep = result.stdout.strip()
        except Exception:
            local_ep = input("Paste your local Globus Connect Personal endpoint UUID: ").strip()
    else:
        local_ep = LOCAL_ENDPOINT

    print(f"\nLocal endpoint:   {local_ep}")
    print(f"Polaris endpoint: {POLARIS_ENDPOINT}")
    print(f"Source:           {LOCAL_PSEUDO_DIR}")
    print(f"Destination:      {POLARIS_DEST}")

    # --- Initiate transfer ---
    tdata = globus_sdk.TransferData(
        tc,
        source_endpoint=local_ep,
        destination_endpoint=POLARIS_ENDPOINT,
        label="QE-MCP pseudopotentials",
        sync_level="checksum",  # only copy files that have changed
    )

    # Add every file in the pseudopotential directory
    pseudo_files = list(LOCAL_PSEUDO_DIR.glob("*.upf")) + list(LOCAL_PSEUDO_DIR.glob("*.UPF"))
    if not pseudo_files:
        print(f"\nNo .upf files found in {LOCAL_PSEUDO_DIR}")
        return

    for f in pseudo_files:
        tdata.add_item(str(f), f"{POLARIS_DEST}/{f.name}")

    print(f"\nTransferring {len(pseudo_files)} pseudopotential files...")
    result = tc.submit_transfer(tdata)
    task_id = result["task_id"]
    print(f"Transfer task ID: {task_id}")

    # --- Wait for completion ---
    print("Waiting for transfer to complete", end="", flush=True)
    while not tc.task_wait(task_id, timeout=300, polling_interval=10):
        print(".", end="", flush=True)
    print()

    task = tc.get_task(task_id)
    if task["status"] == "SUCCEEDED":
        print(f"\n✅ Done! {len(pseudo_files)} files staged at:")
        print(f"   {POLARIS_DEST}\n")
        print("Add these to your claude_desktop_config.json env block:")
        print(f'  "QE_POLARIS_PSEUDO": "{POLARIS_DEST}",')
        print(f'  "QE_POLARIS_ENDPOINT": "{POLARIS_ENDPOINT}",')
    else:
        print(f"\n❌ Transfer failed: {task['status']}")
        print(f"   Check: https://app.globus.org/activity/{task_id}")


if __name__ == "__main__":
    main()
