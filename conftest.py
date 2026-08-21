import asyncio
import inspect


def pytest_addoption(parser):
    parser.addini("asyncio_mode", "default mode for asyncio tests", default="auto")


def pytest_configure(config):
    config.addinivalue_line("markers", "asyncio: run the test in an asyncio event loop")


def pytest_pyfunc_call(pyfuncitem):
    if "asyncio" not in pyfuncitem.keywords:
        return None

    test_function = pyfuncitem.obj
    if not inspect.iscoroutinefunction(test_function):
        return None

    arguments = {
        name: pyfuncitem.funcargs[name]
        for name in pyfuncitem._fixtureinfo.argnames
    }
    asyncio.run(test_function(**arguments))
    return True
