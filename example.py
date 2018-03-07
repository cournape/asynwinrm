import asyncio
from aiowinrm import \
    run_cmd, \
    run_ps, \
    run_psrp, \
    build_win_rm_url, \
    ConnectionOptions


def print_output(res):
    std_out, std_err, exit_code = res
    if std_out:
        print('OUTPUT:\r\n', std_out)
    if std_err:
        print('ERROR:\r\n', std_err)


async def run_cmd_print(conn_opts, cmd, params=()):
    res = await run_cmd(conn_opts, cmd, params)
    print_output(res)


async def run_ps_print(conn_opts, script):
    res = await run_ps(conn_opts, script)
    print_output(res)


async def run_psrp_print(conn_opts, script):
    res = await run_psrp(conn_opts, script)
    print_output(res)


if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    connection_options = ConnectionOptions(
        winrm_url=build_win_rm_url('1.2.3.4', use_https=True),
        username='administrator',
        password='password',
        verify_ssl=False,
        loop=loop
    )
    coro = run_psrp_print(connection_options, "Get-WmiObject Win32_OperatingSystem")
    #coro = run_cmd_print(connection_options, "netstat -an")

    loop.run_until_complete(coro)
    loop.close()