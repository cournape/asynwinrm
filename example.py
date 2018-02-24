import asyncio
from aiohttp import BasicAuth
from aiowinrm import run_cmd, run_ps, run_psrp


async def run_cmd_print(host, auth, cmd, params=()):
    """ Returns a callback that prefix every output line by host.
    """
    # if using self signed certificate
    verify_ssl = False

    res = await run_cmd(host, auth, cmd, params, verify_ssl=verify_ssl)
    print(res[0])
    if res[1]:
        print('ERROR:')
        print(res[1])


async def run_ps_print(host, auth, script):
    # if using self signed certificate
    verify_ssl = False

    res = await run_ps(host, auth, script, verify_ssl=verify_ssl)
    print(res[0])
    if res[1]:
        print('ERROR:')
        print(res[1])


async def run_psrp_print(host, auth, script):
    # if using self signed certificate
    verify_ssl = False

    res = await run_psrp(host, auth, script, verify_ssl=verify_ssl)
    print(res[0])
    if res[1]:
        print('ERROR:')
        print(res[1])


if __name__ == '__main__':
        host = "https://192.168.1.137"
        auth = BasicAuth("administrator", "jurren123.")
        loop = asyncio.get_event_loop()
        coro = run_psrp_print(host, auth, "Get-WmiObject Win32_OperatingSystem")

        loop.run_until_complete(coro)
        loop.close()