import os
import numpy as np
import pandas as pd
import apogee_tools as ap
from astropy.table import Table
from astropy.io import fits, ascii
from astroquery.simbad import Simbad
import wget

db_path = os.environ['APOGEE_DATA'] 
AP_PATH = db_path

data_releases = {'dr10':'allStar-v304.fits', 'dr11':'allStar-v402.fits', \
    'dr12':'allStar-v603.fits', 'dr13':'allStar-l30e.2.fits', 'dr14':'allStar-l31c.2.fits', 'dr15':'allStar-l31c.2.fits'} 


def searchStars(**kwargs):

    """
    Searching DR12-DR13 Databases
    https://data.sdss.org/datamodel/files/APOGEE_REDUX/APRED_VERS/APSTAR_VERS/ASPCAP_VERS/RESULTS_VERS/allStar.html
    @Christian Aganze

    Input:  'id_name' : 2MASS name
            'rel'     : data release to search 
    (note: I realized the latest data release is a compilation of all previous data releases, so DR10-DR12 are unnecessary to search)

    Output: 'apogee_id', 'location_id' : needed to download spectra
    """

    searchval = kwargs.get('id_name')
    release   = kwargs.get('rel', 'dr15')
    ap_path   = kwargs.get('ap_path', AP_PATH)

    #Read the database file
    hdu        = fits.open(ap_path + '/' + data_releases[release])
    keys       = hdu[1].header
    search_par = kwargs.get('SearchPar', 'APOGEE_ID')
    t          = hdu[1].data[search_par]
    condition  = np.where(t==searchval)[0]
    ap_id      = hdu[1].data['APOGEE_ID'][condition]
    asp_id     = hdu[1].data['ASPCAP_ID'][condition]
    loc_id     = hdu[1].data['LOCATION_ID'][condition]

    print(ap_id, loc_id)

    return ap_id, loc_id[0]


def searchVisits(**kwargs):

    """
    Search visits data file allVisit-l30e.2.fits, which should be stored in the folder set as environmental variable 'APOGEE_DATA'
    @Jessica Birky

    Input:  'id_name' : 2MASS name

    Output: 'ap_id', 'plates', 'mjds', 'fibers' : info needed to download visit spectra
    """

    ap_id   = kwargs.get('id_name')
    ap_path = kwargs.get('ap_path', AP_PATH)

    #Read the database file
    hdu = fits.open(ap_path + '/allVisit-l31c.2.fits')

    keys = hdu[1].header
    data = hdu[1].data

    search = data['APOGEE_ID']
    pos = np.where(search == ap_id)

    plates = data['PLATE'][pos]
    mjds = data['MJD'][pos]
    fibers = data['FIBERID'][pos]

    return ap_id, plates, mjds, fibers


def download(star_id, **kwargs):

    """
    Download star by 2MASS name
    @Jessica Birky

    Input:  'star_id' : 2MASS name
            'type'    : aspcap, apstar, or apvisit
    """

    dr = kwargs.get('rel', 'dr15')

    # Datatypes to download
    d_type = kwargs.get('type','aspcap').lower()

    # Get download directory; create if it doesn't already exist
    default_dir = AP_PATH + '/%s_data/' %(d_type)
    ## download to external drive
    #default_dir = '/Volumes/LaCie/apogee/apvisit/'
    dl_dir  = kwargs.get('dir', default_dir)
    ap_path = kwargs.get('ap_path', AP_PATH)

    # Make sure id is in the proper 2MASS format
    if '+' in star_id:
        star_id = '2M' + star_id.split('+')[0][-8:] + '+' + star_id.split('+')[1]
    elif '-' in star_id:
        star_id = '2M' + star_id.split('-')[0][-8:] + '-' + star_id.split('-')[1]
    else:
        print('Designation improperly formated. Must be form "__00034394+8606422".')

    if not os.path.exists(dl_dir):
        os.makedirs(dl_dir)

    key = {'dr13': ['r6','l30e','l30e.2'], 'dr14': ['r8','l31c','l31c.2'], 'dr15': ['r8','l31c','l31c.2']}

    if d_type == 'aspcap':

        """
        Name format for the file: aspcapStar-r8-l31c.2-APOGEE_ID.fits
        """

        fname = 'aspcapStar-{}-{}-{}.fits'.format(key[dr][0], key[dr][2], star_id)

        #check if file has already been downloaded
        if fname not in os.listdir(dl_dir):

            #Look up location id from allStar-l30e.2.fits file
            ap_id, loc_id = searchStars(id_name=star_id, rel=dr, ap_path=ap_path)

            if len(ap_id) != 0:  
                #1. Try downloading from the 2.5m survey
                print('Downloading {} from {} 2.5m survey.'.format(ap_id, dr))
                cwd = os.getcwd()
                main_url = "https://{}.sdss.org/sas/{}/apogee/spectro/redux/{}/stars/{}/{}/{}/{}".format(dr, dr, key[dr][0], key[dr][1], key[dr][2], loc_id, fname)
                os.chdir(dl_dir)
                os.system("curl -O {}".format(main_url))
                #os.system("wget {} -P {}" .format(main_url, dl_dir))
                os.chdir(cwd) 
                
                #2. If not in main survey, try downloading from the 1m survey
                if fname not in os.listdir(dl_dir):
                    print(star_id + ' not found in APOGEE 2.5m survey.')
                    print('Downloading {} from {} 1.0m survey.'.format(ap_id, dr))
                    cwd = os.getcwd()
                    anc_url = "https://data.sdss.org/sas/{}/apogee/spectro/redux/{}/stars/{}/{}/Mdwarfs/{}".format(dr, key[dr][0], key[dr][1], key[dr][2], fname)
                    os.chdir(dl_dir)
                    os.system("curl -O {}".format(anc_url))
                    #os.system("wget {} -P {}" .format(anc_url, dl_dir))
                    os.chdir(cwd)
                
                #3. If not in main or Mdwarf ancilliary survey, return error message
                if fname not in os.listdir(dl_dir):
                    print(fname + ' could not be found in {} or {} \n'.format(main_url, anc_url))
                else:
                    print(fname + ' successfully downloaded. \n')
            else:
                print(star_id + ' does not exist in ' + dr)

        else:
            print('Already have file for ' + star_id)


    if d_type == 'apstar': 

        """
        Name format for the file: apStar-r8-APOGEE_ID.fits
        """

        fname = 'apStar-r8-'+star_id+'.fits'
        
        #check if file has already been downloaded
        if fname not in os.listdir(dl_dir):

            #Look up location id from allStar-l30e.2.fits file
            ap_id, loc_id = searchStars(id_name=star_id, ap_path=ap_path)

            if len(ap_id) != 0:
                #1. Try downloading from the 2.5m survey
                print('Downloading {} from {} 2.5m survey.'.format(ap_id, dr))
                cwd = os.getcwd()
                main_url = "https://{}.sdss.org/sas/{}/apogee/spectro/redux/{}/stars/apo25m/{}/{}".format(dr, dr, key[dr][0], loc_id, fname)
                os.chdir(dl_dir)
                os.system("curl -O {}".format(main_url))
                #os.system("wget -P {} {}" .format(main_url, dl_dir))
                os.chdir(cwd)
                
                #2. If not in main survey, try downloading from the 1m survey
                if fname not in os.listdir(dl_dir):
                    print(star_id + ' not found in APOGEE 2.5m survey.')
                    print('Downloading {} from {} 1.0m survey.'.format(ap_id, dr))
                    anc_url = "https://data.sdss.org/sas/{}/apogee/spectro/redux/{}/stars/apo1m/Mdwarfs/{}".format(dr, key[dr][0], fname)
                    os.system("wget -P {} {}" .format(anc_url, dl_dir)) 
                    
                #3. If not in main or Mdwarf ancilliary survey, return error message
                if fname not in os.listdir(dl_dir):
                    print(fname + ' could not be found in {} or {} \n'.format(main_url, anc_url))
                else:
                    print(fname + ' successfully downloaded. \n')
            else:
                print(star_id + ' does not exist in ' + dr)

        else:
            print('Already have file for ' + star_id)


    if d_type == 'apvisit': 

        """
        Name format for the file: apVisit-APOGEE_ID-NVISIT.fits
        """

        ap_id, plates, mjds, fibers = searchVisits(id_name=star_id, ap_path=ap_path)
        nVisits = len(plates)
        
        if len(ap_id) != 0:

            #Download individual visit .fits files
            for v in range(nVisits):

                #Look up plate, mjd and fiber numbers from allVisit-l30e.2.fits file
                plate, mjd, fiber = str(plates[v]), str(mjds[v]), str(fibers[v])
                
                #make sure fiber string has proper number of zeros 
                fiber = fiber.zfill(3)

                dl_name   = 'apVisit-{}-{}-{}-{}.fits'.format(key[dr][0], plate, mjd, fiber)
                save_name = 'apVisit-{}-{}.fits'.format(star_id, str(v+1))
                print("https://data.sdss.org/sas/{}/apogee/spectro/redux/{}/apo25m/{}/{}/{}".format(str(dr), key[dr][0], plate, mjd, dl_name))
                #check if file has already been downloaded
                if save_name not in os.listdir(dl_dir):
                    print(os.listdir(dl_dir))
                    #1. Try downloading from the 2.5m survey
                    if plate != 'Mdwarfs':
                        print('Downloading {} from {} 2.5m survey.'.format(ap_id, dr))
                        main_url = "https://data.sdss.org/sas/{}/apogee/spectro/redux/{}/apo25m/{}/{}/{}".format(str(dr), key[dr][0], plate, mjd, dl_name)
                        #download_file = 
                        wget.download(main_url, dl_dir+dl_name)
                        os.rename(dl_dir+dl_name, dl_dir+save_name)
                        #os.system("wget {} -O {}/{}".format(main_url, dl_dir, save_name))
                    else:
                        dl_name   = 'apVisit-{}-{}-{}.fits'.format(key[dr][0], mjd, star_id)

                    #2. If not in main survey, try downloading from the 1m survey
                    if save_name not in os.listdir(dl_dir):
                        print(star_id + ' not found in APOGEE 2.5m survey.')
                        print('Downloading {} from {} 1.0m survey.'.format(ap_id, dr))
                        anc_url = "https://data.sdss.org/sas/{}/apogee/spectro/redux/{}/apo1m/{}/{}/{}".format(str(dr), key[dr][0], plate, mjd, dl_name)
                        #download_file = 
                        wget.download(anc_url)
                        os.rename(dl_name, save_name)
                        #os.system("wget {} -O {}/{}".format(anc_url, dl_dir, save_name))

                    #3. If not in main or Mdwarf ancilliary survey, return error message
                    if save_name not in os.listdir(dl_dir):
                        print(dl_name + ' could not be found in {} or {} \n'.format(main_url, anc_url))
                    else:
                        print('{} successfully downloaded as {}. \n'.format(dl_name, save_name))
                else:
                    print('Already have file for ' + star_id)

        else:
            print(star_id + ' does not exist in ' + dr)


    if d_type == 'ap1d':

        """
        Name format for the file: ap1d-APOGEE_ID-NVISIT-CHIP.fits
        """
        
        visit = kwargs.get('visit', 1)
        frame = kwargs.get('frame', 1)

        d_type = 'ap1d'
        default_dir = AP_PATH + '/{}_data/' .format(d_type)
        dl_dir = kwargs.get('dir', default_dir)
        
        print('Retrieving files for {}, VISIT{}, FRAME{}... \n'.format(star_id, visit, frame))
        urls = ap.get_1dspec_urls(star_id, nvisit=visit, frame_id=frame, dir=ap_path)
        chips = ['a', 'b', 'c']

        try:
            url_list = urls['visit%s'%(visit)]['FRAME%s'%(frame)]
            
            for i in range(len(url_list)):
                dl_name = 'ap1D' + url_list[i].split('ap1D')[1]
                save_name = 'ap1d-{}-{}-{}.fits' .format(star_id, visit, chips[i])

                #check if file has already been downloaded
                if save_name in os.listdir(dl_dir):
                    print('Already have file {}'.format(dl_name))
                elif save_name not in os.listdir(dl_dir):
                    print('Downloading {} to apogee_data/ap1d_data/{} \n'.format(url_list[i], save_name))
                    #os.system("wget {} -O {}/{}".format(url_list[i], dl_dir, save_name))
                    wget.download(url_list[i], dl_dir+dl_name)
                else:
                    print('Unable to download file {}'.format(dl_fname))
                
        except:
            print('Unable to retrieve file from urls: {}'.format(urls))
            print('May be due to improperly specified visit or frame number.')


def multiParamSearch(**kwargs):

    """
    Search allStar file for stars in specific ranges for a parameter (or multiple parameters)
    @Jessica Birky

    Input:  'par'    : names of parameters to filter by (ex: 'TEFF', 'LOGG', 'M_H'...)
            'select' : range of values for each parameter (must be in same order as 'par')
            'dir'    : directory where you want to save search table

    Output: data table of stars matching search criteria; printed and saved as csv
    """

    search_par = kwargs.get('par', ['TEFF'])
    select     = kwargs.get('select', [[3000, 4500]])
    save       = kwargs.get('save', True)
    release    = kwargs.get('rel', 'dr14')

    # default save directory is in your APOGEE_DATA environmental variable folder
    if not os.path.exists(AP_PATH + '/tables'):
        os.makedirs(AP_PATH + '/tables')
    output_dir = kwargs.get('dir', AP_PATH + '/tables')

    database = db_path + '/' +data_releases[release]
    data = Table(fits.open(database)[1].data)

    # redefine model parameters to FERRE if requested
    if kwargs.get('model','ATLAS9') == 'MARCS' or kwargs.get('model','ATLAS9') == 'FERRE':
        t = data['TEFF']
        t = t[t>0.]
        print(np.min(t))
        select_cols = ['TEFF','LOGG','VMICRO','M_H','C_M','N_M','ALPHA_M','VSINI']
        for i,s in enumerate(select_cols):
            data[s] = [x[i] for x in data['FPARAM']]
	# need to also add in replace uncertainties
        t = data['TEFF']
        t = t[t>0.]
        print(np.min(t))

    for i in range(len(search_par)):
        p = data[search_par[i]]
        if isinstance(select[i][0], type('k')):
            # matching by strings
            condition = [j for j in range(0, len(data[search_par[i]]))  if data[search_par[i]][j] in select[i]]

        else:
            print(" ALL stars with ", search_par[i], "between", select[i])
            condition = np.where((p>=select[i][0] ) & (p<=select[i][1]))[0]
        data = data[condition]

    # Put only interesting values into the data table: 2MASS name and aspcap parameters
    data_dict  = {'2MASS_ID':data['APOGEE_ID'], 'TEFF':data['TEFF'], 'LOGG':data['LOGG'], 'M_H':data['M_H']}
    data_table = pd.DataFrame(data=data_dict)

    fname = kwargs.get('fname', 'search.csv')
    if save == True:
        save_dir = '%s/%s' %(output_dir, fname)
        data_table.to_csv(save_dir)
        print('Table saved to ', save_dir)

    return data


def returnAspcapTable(tm_ids, **kwargs):

    """
    Return a table of parameters (in csv format) for a list of APOGEE spectra by 2MASS name
    """

    default_params = [  'APOGEE_ID', 'TEFF', 'LOGG', 'M_H', \
                        'J', 'J_ERR', 'H', 'H_ERR', 'K', 'K_ERR', \
                        'WASH_M', 'WASH_M_ERR', 'WASH_T2', 'WASH_T2_ERR', \
                        'DDO51', 'DDO51_ERR', \
                        'WASH_DDO51_GIANT_FLAG', 'WASH_DDO51_STAR_FLAG', \
                        'RA', 'DEC', 'SNR' ]

    # optional
    params = kwargs.get('par', default_params)
    save   = kwargs.get('save', False)
    output = kwargs.get('out', 'aspcap_table.fits')

    database = db_path + '/allStar-l31c.2.fits'
    data = Table(fits.open(database)[1].data)

    index = [np.where(data['APOGEE_ID'] == TMID)[0][0] for TMID in tm_ids]

    data_dict  = {params[i]: data[params[i]][index] for i in range(len(params))}
    # data_table = pd.DataFrame(data=data_dict)

    if save == True:
        # data_table.to_csv('tables/'+output)
        t = Table(list(data_dict.values()), names=tuple(data_dict.keys()))
        t.write('tables/'+str(output), format='fits')

    return data_dict


def returnSimbadParams(id_list):

    """
    Enter list of 2MASS IDs, and return stellar parameters from simbad
    @Jessica Birky

    Input:  'id_list' : list of 2MASS IDs

    Output: 'result' : table of stellar parameters obtained from simbad
    """

    customSimbad = Simbad()
    customSimbad.add_votable_fields('fe_h', 'rv_value', 'rvz_error', 'sptype', 'rot')
    customSimbad.get_votable_fields()

    objects = []
    no_entry = 0
    
    for s in id_list:
        ID = str(s)
        obj = customSimbad.query_object(ID)

        try:
            spt = str(obj['SP_TYPE']).split('-\n')[1]
            d = {'ID':str(s), 'SPT':spt, 'TEFF':obj['Fe_H_Teff'], 'LOGG':obj['Fe_H_log_g'], \
                 'FE_H':obj['Fe_H_Fe_H']} 
            df = pd.DataFrame(data=d)
            objects.append(df)
        except:
            no_entry += 1

    print('No simbad values for ' + no_entry + ' objects.')

    result = pd.concat(objects)

    return result




