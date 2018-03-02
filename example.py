import asyncio
from aiohttp import BasicAuth
from aiowinrm import run_cmd, run_ps, run_psrp


async def run_cmd_print(host, auth, cmd, params=()):
    verify_ssl = False  # if using self signed certificate

    res = await run_cmd(host, auth, cmd, params, verify_ssl=verify_ssl)
    std_out, std_err, exit_code = res
    if std_err:
        print('ERROR:\r\n', std_err)


async def run_ps_print(host, auth, script):
    verify_ssl = False  # if using self signed certificate

    res = await run_ps(host, auth, script, verify_ssl=verify_ssl)
    std_out, std_err, exit_code = res
    if std_err:
        print('ERROR:\r\n', std_err)


async def run_psrp_print(host, auth, script):
    verify_ssl = False  # if using self signed certificate

    res = await run_psrp(host, auth, script, verify_ssl=verify_ssl)
    std_out, std_err, exit_code = res
    if std_err:
        print('ERROR:\r\n', std_err)


if __name__ == '__main__':
    host = "https://1.2.3.4"
    auth = BasicAuth("administrator", "password")
    loop = asyncio.get_event_loop()
    coro = run_psrp_print(host, auth, "Get-WmiObject Win32_OperatingSystem")
    # coro = run_cmd_print(host, auth, "netstat -an")

    loop.run_until_complete(coro)
    loop.close()