from os.path import exists

from cornice.service import Service
from pkg_resources import get_distribution

from ..config import path, get_logger


log = get_logger(__name__)


app_info = Service(
    name='appinfo',
    path=path(''),
    renderer='json',
    accept='application/json')


@app_info.get()
def get_app_info(request):
    result = dict(
        version=get_distribution('senic_hub').version,
        bin_path=request.registry.settings['bin_path'],
        onboarded=is_hub_onboarded(request)
    )
    return result


def is_hub_onboarded(request):
    nuimo_app_config_path = request.registry.settings['nuimo_app_config_path']
    devices_path = request.registry.settings['devices_path']
    homeassistant_config_path = request.registry.settings['homeassistant_config_path']

    return (exists(nuimo_app_config_path) and
            exists(devices_path) and
            exists(homeassistant_config_path))
