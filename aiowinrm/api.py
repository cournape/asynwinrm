from base64 import b64encode

from aiowinrm.command_context import CommandContext
from aiowinrm.ps_context import PowerShellContext
from aiowinrm.shell_context import ShellContext
from aiowinrm.utils import check_for_bom, _clean_error_msg


async def run_cmd(connection_options,
                  command,
                  args=(),
                  env=None,
                  cwd=None):
    """
    Run the given command on the given host asynchronously.
    """
    async with ShellContext(connection_options, env=env, cwd=cwd) as shell_context:
        async with CommandContext(shell_context, command, args) as command_context:
            return_code = None
            stdout_buffer, stderr_buffer = [], []
            is_done = False
            while not is_done:
                stdout, stderr, return_code, is_done = await command_context.output_request()
                stdout_buffer.append(stdout)
                stderr_buffer.append(stderr)
            return ''.join(stdout_buffer), ''.join(stderr_buffer), return_code


async def run_ps(connection_options,
                 script):
    """
    run PowerShell script over cmd+powershell

    :param connection_options:
    :param script:
    :return:
    """
    check_for_bom(script)
    encoded_ps = b64encode(script.encode('utf_16_le')).decode('ascii')
    res = await run_cmd(connection_options,
                        command=f'powershell -encodedcommand {encoded_ps}')
    stdout, stderr, return_code = res
    if stderr:
        # if there was an error message, clean it it up and make it human
        # readable
        stderr = _clean_error_msg(stderr)
    return stdout, stderr, return_code


async def run_psrp(connection_options,
                   script):
    """
    run PowerShell script over PSRP protocol

    :param connection_options:
    :param script:
    :return:
    """
    check_for_bom(script)
    async with PowerShellContext(connection_options) as pwr_shell_context:
        stdout_buffer, stderr_buffer = [], []
        command_id = await pwr_shell_context.start_script(script)
        exit_code = None
        while exit_code is None:
            res = await pwr_shell_context.get_command_output(command_id)
            std_out, std_err, exit_code = res
            stdout_buffer.append(std_out)
            stderr_buffer.append(std_err)
    return ''.join(stdout_buffer), ''.join(stderr_buffer), exit_code
