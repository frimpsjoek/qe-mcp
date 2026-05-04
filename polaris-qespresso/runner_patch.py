"""
runner_patch.py

Replace the get_runner() function at the bottom of:
    qe_mcp/core/runner.py

with the version below. That's the only change needed in runner.py.
"""


def get_runner(config) -> "QERunner":
    """Get appropriate runner based on QE_RUNNER environment variable."""
    import os

    runner_type = os.environ.get("QE_RUNNER", "docker" if config.use_docker else "local")

    if runner_type == "globus":
        endpoint = os.environ.get("QE_GLOBUS_ENDPOINT")
        function = os.environ.get("QE_GLOBUS_FUNCTION")
        if not endpoint or not function:
            raise RuntimeError(
                "QE_RUNNER=globus requires QE_GLOBUS_ENDPOINT and "
                "QE_GLOBUS_FUNCTION environment variables."
            )
        from qe_mcp.core.globus_runner import GlobusComputeRunner
        runner = GlobusComputeRunner(endpoint_uuid=endpoint, function_uuid=function)
        if not runner.check_available():
            raise RuntimeError(
                f"Globus Compute endpoint {endpoint} is not online. "
                "SSH to Polaris and run: globus-compute-endpoint start qe-polaris-1"
            )
        return runner

    elif runner_type == "docker" or config.use_docker:
        runner = DockerQERunner(config.docker_image)
        if runner.check_available():
            return runner
        raise RuntimeError(
            f"Docker runner requested but image '{config.docker_image}' not available. "
            "Build it with: docker build -t qe-local ."
        )

    else:
        runner = LocalQERunner(config)
        if runner.check_available():
            return runner
        raise RuntimeError(
            "Local QE executables not found. "
            "Set QE_PREFIX environment variable or use Docker mode."
        )
