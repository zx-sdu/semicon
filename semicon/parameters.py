import pandas as pd
import os

from scipy.constants import physical_constants
from scipy.interpolate import interp1d
from types import SimpleNamespace
import numpy as np

import matplotlib.pyplot as plt


######  general constants and globals
c = physical_constants['speed of light in vacuum'][0]
val_hbar = physical_constants['Planck constant over 2 pi in eV s'][0]
val_m0 = physical_constants['electron mass energy equivalent in MeV'][0]
val_m0 = val_m0 / (c*10**9)**2 * 10**6
val_mu_B = physical_constants['Bohr magneton in eV/T'][0]
val_phi_0 = 2 * physical_constants['mag. flux quantum'][0] * (10**9)**2
taa = val_hbar**2 / 2.0 / val_m0

constants = {
    'm_0': val_m0,
    'phi_0': val_phi_0,
    'mu_B': val_mu_B,
    'hbar': val_hbar
}

###### loading parameters from databank
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

_banks_names = ['winkler', 'lawaetz']
def load_params(bankname):
    """Load material parameters from specified databank.

    output: pandas dataframe
    """
    if bankname not in _banks_names:
        msg = "Unkown bankname. Possible options are {}"
        raise ValueError(msg.format(_banks_names))
    fname = 'bank_' + bankname + '.csv'
    fpath = os.path.join(BASE_DIR, 'databank', fname)
    return pd.read_csv(fpath, index_col=0)


###### renormalization of parameters
def renormalize_parameters(dict_pars, new_gamma_0=None,
                           bands=('gamma_6c', 'gamma_8v', 'gamma_7v')):
    """Renormalize parameters"""

    output = {}

    p = SimpleNamespace(**dict_pars)
    Ep = p.P**2 / taa
    output['P'] = p.P
    output['E_v'] = p.E_v
    output['E_0'] = p.E_0
    output['Delta_0'] = p.Delta_0

    # gamma_6c parameters
    if 'gamma_6c' in bands:
        # do special steps if user want to renormalize gamma_0
        if new_gamma_0 is not None:
            if ('gamma_8v' not in bands) or ('gamma_7v' not in bands):
                raise ValueError('Cannot set different "gamma_0" '
                                 'without at least one hole band.')
            scale = 0
            if 'gamma_8v' in bands:
                scale += (2/3) / p.E_0

            if 'gamma_7v' in bands:
                scale += (1/3) / (p.E_0 + p.Delta_0)

            Ep = (p.gamma_0 - new_gamma_0) / scale
            output['P'] = np.sqrt(taa * Ep)
            output['gamma_0'] = new_gamma_0

        else:
            output['gamma_0'] = p.gamma_0
            if 'gamma_8v' in bands:
                output['gamma_0'] -= (2/3) * (Ep / p.E_0)

            if 'gamma_7v' in bands:
                output['gamma_0'] -= (1/3) * (Ep / (p.E_0 + p.Delta_0))

        # g-factor
        output['g_c'] = p.g_c
        if 'gamma_8v' in bands:
            output['g_c'] += (2/3) * (Ep / p.E_0)

        if 'gamma_7v' in bands:
            output['g_c'] -= (2/3) * (Ep / (p.E_0 + p.Delta_0))

    # now the gamma_7v and gamma_8v parameters
    if ('gamma_8v' in bands) or ('gamma_7v' in bands):
        output['gamma_1'] = p.gamma_1
        output['gamma_2'] = p.gamma_2
        output['gamma_3'] = p.gamma_3
        output['kappa'] = p.kappa
        output['q'] = p.q

        if 'gamma_6c' in bands:
            output['gamma_1'] -= (1/3) * (Ep / p.E_0)
            output['gamma_2'] -= (1/6) * (Ep / p.E_0)
            output['gamma_3'] -= (1/6) * (Ep / p.E_0)
            output['kappa'] -= (1/6) * (Ep / p.E_0)

    return output


###### system specific parameter functions
def bulk(bank, material, new_gamma_0=None, valence_band_offset=0.0,
         bands=('gamma_6c', 'gamma_8v', 'gamma_7v'),
         extra_constants=None):
    """Get bulk parameters of a specified material."""
    df_pars = load_params(bank)
    dict_pars = df_pars.loc[material].to_dict()
    dict_pars['gamma_0'] = 1 / dict_pars.pop('m_c')
    dict_pars['E_v'] = valence_band_offset

    output = renormalize_parameters(dict_pars, new_gamma_0, bands)

    if extra_constants is not None:
        output.update(extra_constants)

    return output


def two_deg(bank, materials, widths, valence_band_offsets, grid_spacing,
            new_gamma_0=None, bands=('gamma_6c', 'gamma_8v', 'gamma_7v'),
            extra_constants=None):
    """Get parameter functions for a specified 2D system.


    To do:
    - way provide parameters, not only data "bank" name,
    - specify which parameters should be varied (default all defined parameters)
    """

    def get_walls(a, Ws):
        walls = np.array([sum(Ws[:(i+1)]) for i in range(len(Ws)-1)]) - 0.5 * a
        walls = np.insert(walls, 0, -a)
        walls = np.append(walls, sum(Ws))
        return walls

    def interp_sn_params(a, walls, values, parameter_name):
        xs = [x+d for x in walls[1:-1] for d in [-a/2, +a/2]]
        xs = [walls[0]] + xs + [walls[-1]]
        ys = [p[parameter_name] for p in values for i in range(2)]
        return interp1d(xs, ys, fill_value='extrapolate')

    # varied parameters should probably be a union of available k.p parameters,
    varied_parameters = ['E_0', 'E_v', 'Delta_0', 'P', 'kappa', 'g_c',
                         'gamma_0', 'gamma_1', 'gamma_2', 'gamma_3']

    df_pars = load_params(bank)

    parameters = []
    for material, offset in zip(materials, valence_band_offsets):
        dict_pars = df_pars.loc[material].to_dict()
        dict_pars['gamma_0'] = 1 / dict_pars.pop('m_c')
        dict_pars['E_v'] = offset
        dict_pars = renormalize_parameters(dict_pars, new_gamma_0, bands)
        parameters.append(dict_pars)

    walls = get_walls(grid_spacing, widths)

    output = {}
    for par_name in varied_parameters:
        output[par_name] = interp_sn_params(grid_spacing, walls, parameters, par_name)

    if extra_constants is not None:
        output.update(extra_constants)

    return output, walls


###### helper plotting function
def plot_2deg_bandedges(two_deg_params, xpos, walls=None, show_fig=False):
    """Plot band edges """
    y1 = two_deg_params['E_v'](xpos)
    y2 = y1 + two_deg_params['E_0'](xpos)

    fig = plt.figure(figsize=(20, 5))
    plt.plot(xpos, y1, '-o')
    plt.plot(xpos, y2, '-o')

    if walls is not None:
        walls_y = [min([np.min(y1), np.min(y2)]), max([np.max(y1), np.max(y2)])]
        for w in walls:
            plt.plot([w, w], walls_y, 'k--')

    if show_fig:
        plt.show()

    return fig
