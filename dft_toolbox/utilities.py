"""
Created on Wed Jul 27 15:09:58 2022

@author: hnr2 & jac16
"""

import io, os, pkgutil, subprocess
import numpy as np
import pandas as pd
import glob
import json
import warnings

R = 0.0019872042586408316  # kcal/(mol*K)

atomic_num = {
    1: 'H',
    6: 'C',
    7: 'N',
    8: 'O',
    11: 'Na',
    16: 'S',
    17: 'Cl'
}

def modify_coordinates(coords, box_size, wrap_cutoff):
    """
    Returns wrapped coordinate values, for the coordinate_wrapper function which modifies the .xyz file.

    Parameters
    ----------
    coords : list
        A list of coordinates to wrap
    box_size : float
        The exact box size to wrap around
    wrap_cutoff : float
        The exact cutoff distance to wrap beyond in Angstroms

    Returns
    ------
    modified : list
        A wrapped list of coordinates
    """
    modified = [coords[i] - coords[0] for i in range(len(coords))]
    for num, coord in enumerate(modified):
        if coord > wrap_cutoff:
            modified[num] -= box_size
        elif coord < -wrap_cutoff:
            modified[num] += box_size
    return modified


def coordinate_wrapper(fname, box_size, wrap_cutoff):
    """
    Modifies the .xyz file based on the box size to wrap the coordinates.

    Parameters
    ----------
    fname : str
        The path to the .xyz file to be modified
    box_size : float
        The exact box size to wrap around
    wrap_cutoff : float
        The exact cutoff distance to wrap beyond in Angstroms

    Returns
    ------
    Nothing is returned. The provided .xyz file is itself modified.
    """
    coords = np.transpose(extract_coordinates(fname)[1])
    with open(fname, 'r') as f:
        lines = f.readlines()[2:]
    for num, line in enumerate(lines):
        lines[num] = line.split()
    for num, line in enumerate(lines):
        if len(line) == 0:
            lines.remove(lines[num])
    atom_types = []
    for num, line in enumerate(lines):
        atom_types.append(line[0])
    x_coords = modify_coordinates(coords[0], box_size, wrap_cutoff)
    y_coords = modify_coordinates(coords[1], box_size, wrap_cutoff)
    z_coords = modify_coordinates(coords[2], box_size, wrap_cutoff)
    with open(fname, 'w') as f:
        f.write("\n")
        for num, line in enumerate(lines):
            toWrite = '\n' + ' '*10 + atom_types[num] + ' '*10 + f'{x_coords[num]:.5f}' + f'     {y_coords[num]:.5f}' + f'     {z_coords[num]:.5f}'
            f.write(toWrite)

def checkOscillatingJob(runningJobIDs, outputLogs, n_points=5):
    """
    Determine if job is oscillating. Two types: sinusoidal type, such as methyl rotation, or other piecewise oscillation, such as what occurs during optimization of large systems with explicit solvent. This function only supports type 2 for now...

    MAKE SURE THE ".OUT" FILENAMES ARE EQUIVALENT TO THE OUTPUTLOG NUMBERING SCHEME: outputlog#####.txt --> sim#####.out
    Parameters
    ---------
    runningJobIDs : array
        A list of the job IDs of the runing jobs.
    outputLogs : array
        A list of the paths to the output logs.
    n_points : int, Optional, default=5
        Number of times oscillation-type behavior is to occur before it is flagged. Optional, default=5.

    Returns
    ------

    """
    outputLogs.sort()
    jobIDs = []
    for i in range(len(outputLogs)):
        with open(outputLogs[i],'r') as o:
            lines = o.readlines()
        jobIDs.append(lines[0][8:])
    jobIDs = [ID.rstrip('\n') for ID in jobIDs]
    jobsToCheck = [outputLogs[i][outputLogs[i].find('outputlog'):] for i in range(len(outputLogs)) if jobIDs[i] in runningJobIDs]
    jobsToCheck = ["sim{}.out".format(job[job.find('outputlog')+9:job.find('.txt')]) for job in jobsToCheck]
    status = []
    for job in jobsToCheck:
        slurmCommand = 'grep "Step size scaled by" {}'.format(job)
        process = subprocess.Popen(slurmCommand, stdout=subprocess.PIPE, shell=True)
        vals = process.communicate()[0].split('\n')
        grep = [val.rstrip('"').lstrip('"') for val in vals if len(val)>0]
        grep = grep[-n_points:]
        oscillating = True
        for instance in grep:
            if "0.000" in instance:
                continue
            else:
                oscillating = False
        status.append(oscillating)
    return status


def check_job_status(username, errorLogs, outputLogs, print_output=True, save_output=False, filename="job_status.csv"):
    """
    Determine status of G16 job on SLURM. Run this function in a directory in which G16 jobs are running on HPC.

    Parameters
    ----------
    username : str
        Your userID on HPC cluster.
    errorLogs : array
        A list of error logs to parse through.
    outputLogs : array
        A list of output logs to parse through.
    print_output : bool, Optional, default=True
        If True, a list of each category will be printed
    save_output : bool, Optional, default=False
        If True, a csv file with the status of each job will be saved to the csv file ``filename``
    filename : str, Optional, default="job_status.csv"
        Filename for output csv file

    Returns
    ------
    No returned values. Generates .csv file with the job ID numbers, assigned to a status.

    """
    errorLogs.sort()
    outputLogs.sort()

    jobIDs = []
    for i in range(len(outputLogs)):
        with open(outputLogs[i],'r') as o:
            lines = o.readlines()
        jobIDs.append(lines[0][8:])
    jobIDs = [ID.rstrip('\n') for ID in jobIDs]

    slurmCommand = 'squeue -u {} --noheader --format="%A"'.format(username)
    process = subprocess.Popen(slurmCommand, shell=True, stdout=subprocess.PIPE)
    vals = process.communicate()[0].split('\n')
    squeue = [val.rstrip('"').lstrip('"') for val in vals if len(val)>0]

    running = []
    for i in range(len(jobIDs)):
        if jobIDs[i] in squeue:
            running.append(jobIDs[i])

    oscillatingStatus = checkOscillatingJob(running, outputLogs)
    oscillatingStatus = [running[i] for i in range(len(running)) if oscillatingStatus[i] ]

    failed = []
    completed = []
    for i in range(len(errorLogs)):
        if jobIDs[i] in running:
            continue
        with open(errorLogs[i],'r') as e:
            lines = e.readlines()
        for line in lines:
            if "error" in line or "Error" in line or "ERROR" in line:
                failed.append(jobIDs[i])
                break
            else:
                if jobIDs[i] not in running and jobIDs[i] not in completed:
                    completed.append(jobIDs[i])
    if print_output:
        print("Running: {}".format(", ".join(running)))
        print("Oscillating: {}".format(", ".join(oscillatingStatus)))
        print("Complete: {}".format(", ".join(complete)))
        print("Failed: {}".format(", ".join(failed)))
    if save_output:
        with open(filename, "w") as f:
            f.write("JobID, Status")
            for job in running:
                f.write("{}, {}".format(job,"In Progress"))
            for job in oscillatingStatus:
                f.write("{}, {}".format(job,"Oscillating"))
            for job in failed:
                f.write("{}, {}".format(job,"Failed"))
            for job in complete:
                f.write("{}, {}".format(job,"Complete"))


def boltzmannG(G, beta):
    """
    Calculate Boltzmann distribution expectation value of a free energy term.

    Parameters
    ----------
    G : np.ndarray(dtype=np.float)
        The array containing the samples to be averaged.
    beta : np.ndarray(dtype=np.float)
        An array containing the value of (1/RT) for each value in G (i.e., same length as G). This format is required in order to calculate error bars with bootstrapping.

    Returns
    ------
    averagedG : float
        The Boltzmann averaged value of the G samples provided.

    """
    G = np.array(G, dtype=np.float128)
    arr1 = [np.exp(-(val) * beta[i]) for i,val in enumerate(G)]
    Q = sum(arr1)
    pxi = np.array(arr1) / Q
    averagedG = np.float64(np.dot(G, pxi))
    return averagedG


def boltzmannH(G, H, beta):
    """
    Calculate Boltzmann distribution expectation value of an enthalpy term. Probabilities calculated with free energy values.

    Parameters
    ----------
    H : np.ndarray(dtype=np.float)
        The array containing the samples to be averaged.
    beta : np.ndarray(dtype=np.float)
        An array containing the value of (1/RT) for each value in G (i.e., same length as G). This format is required in order to calculate error bars with bootstrapping.

    Returns
    ------
    averagedG : float
        The Boltzmann averaged value of the H samples provided.

    """
    G = np.array(G, dtype=np.float128)
    H = np.array(H, dtype=np.float128)
    arr1 = [np.exp(-(val) * beta[i]) for val in G]
    Q = sum(arr1)
    pxi = np.array(arr1) / Q
    averagedH = np.float64(np.dot(H, pxi))
    return averagedH


def boltzmannS(G, S, beta):
    """
    Calculate Boltzmann distribution expectation value of an entropy term, including both the weighted term and the Gibbs term. Probabilities calculated with free energy values.

    Parameters
    ----------
    S : np.ndarray(dtype=np.float)
        The array containing the samples to be averaged.
    beta : np.ndarray(dtype=np.float)
        An array containing the value of (1/RT) for each value in G (i.e., same length as G). This format is required in order to calculate error bars with bootstrapping.

    Returns
    ------
    averagedG : float
        The Boltzmann averaged value of the S samples provided.

    """
    G = np.array(G, dtype=np.float128)
    S = np.array(S, dtype=np.float128)
    arr1 = [np.exp(-(val) * beta[i]) for val in G]
    Q = sum(arr1)
    pxi = np.array(arr1) / Q
    weightedS = np.dot(S, pxi)
    gibbsS = (-1) * R * np.dot(pxi, np.log(pxi))
    averagedS = np.float64((weightedS + gibbsS))
    return averagedS


# calc free energy IN SOLUTION. To get free energy OF SOLVATION, calculate this function first, then subtract gas-phase free energy of solute calculated at same level of theory and gas-phase standard state correction, giving delta-G of solvation.
def calc_pQCT(gas_free_energy_cluster, gas_free_energy_H2O, pcm_dG_solv, n_water, dG_solv_H2O=-1.34, temp=298.15):
    """
    Calculate free energy in solution G_aq using pQCT method, monomer cycle. In kcal/mol.

    Parameters
    ----------
    gas_free_energy_cluster : float
        The value of the free energy of a given solute-water cluster in the gas-phase, calculated using the other available functions in this package.
    gas_free_energy_H2O : float
        The value of the free energy of a single water molecule in the gas-phase, calculated using the other available functions in this package (i.e., starting with a G16 opt/freq calculation on a single H2O molecule at the same level of theory as the other calculations).
    pcm_dG_solv : float
        The value of the free energy of solvation of the given solute-water cluster, calculated by an externaliteraiton PCM calculation with 1stvac option, and extracted by the dGSolvPCM function in this package.
    n_water : int
        The number of water molecules surrounding the solute.
    dG_solv_H2O : float, Optional, default=-1.34
        The free energy of solvation of a single water molecule, as caculated by PCM continuum solvent at the same level of theory as the other calculations conducted. Optional, default=-1.34, which is calculated at RB3LYP-D3/aug-cc-pVDZ, including cavitation and dispersion-repulsion energies.
    temp : float, Optional, default=298.15
        Specify the absolute temperature (K) to calculate thermo at. Optional, default=298.15.

    Returns
    ------
    G_aq : float
        The value of the free energy in solution. To get free energy OF SOLVATION, calculate this function first, then subtract gas-phase free energy of solute calculated at same level of theory and gas-phase standard state correction, giving delta-G of solvation.
    """
    G_aq = (
        (gas_free_energy_cluster + R * temp * np.log(24.46))
        - n_water * (gas_free_energy_H2O + R * temp * np.log(24.46))
        + pcm_dG_solv
        - n_water * dG_solv_H2O
        - n_water * R * temp * np.log(1000 / 18.01528)
    )
    return G_aq


def calc_thermo_NASA(coeffs, temp=298.15):
    """
    Calculate thermochemical quantities from NASA polynomial coefficients. All values are in kcal/mol or kcal/(mol*K).

    Parameters
    ----------
    coeffs : array
        An array containing the 7 coefficients of the NASA polynomial.
    temp : float, Optional, default=298.15
        Specify the absolute temperature (K) to calculate thermo at. Optional, default=298.15.

    Returns
    ------
    thermo : array
        An array of length 4 returning the thermo at the specified temperture, Cp, H, S, and G.
    """
    cp_t = (
        coeffs[0]
        + temp * coeffs[1]
        + pow(temp, 2) * coeffs[2]
        + pow(temp, 3) * coeffs[3]
        + pow(temp, 4) * coeffs[4]
    ) * R
    H_t = (
        coeffs[0] * temp
        + (pow(temp, 2) / 2) * coeffs[1]
        + (pow(temp, 3) / 3) * coeffs[2]
        + (pow(temp, 4) / 4) * coeffs[3]
        + (pow(temp, 5) / 5) * coeffs[4]
        + coeffs[5]
    ) * R
    S_t = (
        coeffs[0] * np.log(temp)
        + temp * coeffs[1]
        + pow(temp, 2) * (coeffs[2] / 2)
        + pow(temp, 3) * (coeffs[3] / 3)
        + pow(temp, 4) * (coeffs[4] / 4)
        + coeffs[6]
    ) * R
    G_t = H_t - temp * S_t
    thermo = [cp_t, H_t, S_t, G_t]
    return thermo


def calc_thermo_Arkane(fname, temperature=298.15):
    """
    Read chemkin file "chem.inp" output from Arkane thermo() calculations. Determine high/low NASA polynomial coefficients for each "species" within the file, based on input temperature. Return calculated Cp(T), H(T), S(T), G(T) at that temperature. All values are in kcal/mol or kcal/(mol*K).

    Parameters
    ----------
    fname : str
        Specify the complete path to the chem.inp file output from Arkane.
    temperature : float, Optional, default=298.15
        Specify the absolute temperature (K) to calculate thermo at. Optional, default=298.15.

    Returns
    ------
    output_thermo : array-like
        A 2D Numpy array containing the thermo (Cp,H,S,G at specified temperature) of each of the N molecules present in the chem.inp file, of shape (N,4). All values are in kcal/mol or kcal/(mol*K).

    """
    with open(rf"{fname}", "r") as o:
        lines = o.readlines()
    for num, line in enumerate(lines):
        if "THERM" in line:
            lines = lines[num + 3 :]
            break
    for num, line in enumerate(lines):
        if "END" in line:
            lines = lines[: num - 2]
            break
    lines = [line for line in lines if line != "\n"]
    molecules = []
    for num, line in enumerate(lines):
        if num % 4 == 0:
            molecules.append(line.split()[0])
    output_thermo = []
    for i in range(len(molecules)):
        allCoeffs = lines[i * 4 + 1 : (i + 1) * 4]
        nasaPolyHigh = [float(allCoeffs[0][j * 15 : (j + 1) * 15]) for j in range(5)] + [float(allCoeffs[1][j * 15 : (j + 1) * 15]) for j in range(2)]
        nasaPolyLow = [float(allCoeffs[1][j * 15 : (j + 1) * 15]) for j in range(2, 5)] + [float(allCoeffs[2][j * 15 : (j + 1) * 15]) for j in range(4)]
        lowTemp = float(lines[i * 4].split()[-4])
        midTemp = float(lines[i * 4].split()[-2])
        highTemp = float(lines[i * 4].split()[-3])

        coeffs = []
        if temperature >= lowTemp and temperature <= midTemp:
            coeffs = nasaPolyLow
        elif temperature > midTemp and temperature <= highTemp:
            coeffs = nasaPolyHigh
        else:
            return "Temperature out of fitted range. Please input a valid temperature."
        output_thermo.append(calc_thermo_NASA(coeffs, temp=temperature))
    output_thermo = np.reshape(output_thermo, (len(molecules), 4))
    return output_thermo


def create_g16_input(fname, GasRouteSection, PCMRouteSection, coordFile, charge=0, spinMultiplicity=1):
    """
    Create G16 input and associated .slurm submission script, from either a .xyz coordinates file or a CONVERGED .out/.log G16 optimization file.

    Parameters
    ----------
    fname : str
        A string specifying the name of the simulation file to be created. Do not enter a file extension, just the name.
    GasRouteSection : string
        A string specifiying the keywords after the "# " portion of the standard Gaussian route section for the gas-phase opt/freq portion of the job. Do not include the "# ", only the keywords. For example, "opt=calcall freq ..." should be specified in full. All generated simulation files will have this same route section.
    PCMRouteSection : string
        A string specifiying the keywords after the "# " portion of the standard Gaussian route section for the SCRF=PCM portion of the job. MUST INCLUDE "geom=check". Do not include the "# ", only the keywords. For example, "opt=calcall freq ..." should be specified in full. All generated simulation files will have this same route section.
    coordFile : string
        A string containing the complete path of the .xyz coordinate specification file for which Gaussian simulation files should be created.
    charge : int, Optional, default=0
        An integer representing the total formal charge of the overall system. Optional, default=0.
    spinMultiplicity : int, Optional, default=1
        An integer representing the spin state of the system. Optional, default=1.

    Returns
    ------
    There is no output after correct usage of the function. The generated Gaussian job file and associated .slurm script will appear in the directory within which this function is run.
    """
    coords = extract_coordinates(coordFile)[0]
    path, filename = os.path.split(fname)
    if path:
        cwd = os.getcwd()
        if cwd not in path:
            path = os.path.join(cwd,path)
    check_name = os.path.join(path,filename)

    with open(rf"{fname}_gas.com", "w") as n:
        n.writelines(
            [
                f"%chk={check_name}_gas.chk\n",
                f"# {GasRouteSection}\n\n",
                f"G16 gas-phase opt/freq job for {fname}\n\n",
                f"{charge} {spinMultiplicity}\n",
            ]
        )
        n.writelines(coords)
        n.write("\n")
    if "scrf" not in PCMRouteSection:
        PCMRouteSection += " scrf=(iefpcm,solvent=water,externaliteration,1stvac,read)"
    if "geom=check" not in PCMRouteSection:
        PCMRouteSection += " geom=check"

    with open(rf"{fname}_PCM.com", "w") as n2:
        n2.writelines(
            [
                f'%oldchk={check_name}_gas.chk\n',
                f'%chk={check_name}_PCM.chk\n',
                f'# {PCMRouteSection}\n\n',
                f'G16 PCM job for {fname}\n\n',
                f'{charge} {spinMultiplicity}\n',
                f'\ndis\ncav\nrep\n\n\n'
            ]
        )

def create_slurm_script(fname, filename_g16, nodes, partition, mem, time="168:00:00", filename_sterr=None, filename_stout=None, log_path=None):
    """
    Create a .slurm submission script for a given Gaussian 16 job, using a template .slurm script that will automatically assign G16 environment variables in the most efficient setup.
    Parameters
    ----------
    fname : str
        A string specifying the filename of the SLURM submission script job file, NOT including the file extension.
    filename_g16 : str
        A string specifying the filename and relative path for the Gaussian input file, NOT including the file extension. ( Relative to the submission file path defined in ``fname``
    nodes : int
        An integer representing the number of nodes requested.
    partition : str
        A string representing the partition on which the job is to be scheduled.
    mem : int
        An integer representing the amount (in GB) of memory requested. Must be specified to access relevant SLURM environmental variables.
    time : str, Optional, default="168:00:00"
        Job WallClock Max before job is killed. Optional, default="168:00:00", or 7 days.
    filename_stout : str, Optional, default=None
        Filename for standard output, default is: ``stout_{fname.split(os.sep)[-1]}.txt``
    filename_sterr : str, Optional, default=None
        Filename for standard error, default is: ``sterr_{fname.split(os.sep)[-1]}.txt``
    log_path : str, Optional, default=None
        If None, that path (if any) contained in ``fname`` is used to save the gaussian log file, ``log_path + {fname.split(os.sep)[-1]}_X.log`` where ``X`` is "gas" or "PCM".

    Returns
    -------
    There is no output after correct usage of the function. The generated .slurm file will appear in the directory within which this function is run.

    """
    path, filename = os.path.split(fname)
    if filename_sterr == None:
        filename_sterr = "sterr_{}.txt".format(filename)
    if filename_stout == None:
        filename_stout = "stout_{}.txt".format(filename)

    if log_path == None:
        log_path = path

    template = io.TextIOWrapper(io.BytesIO(pkgutil.get_data(__name__, "templates/submissionScriptTemplate")), encoding='utf-8')

    lines = { 1: f'#SBATCH --job-name="{filename}"\n',
              2: f"#SBATCH --nodes={nodes}                         # number of nodes\n",
              3: f"#SBATCH --mem={mem}G                         # memory pool for all cores\n",
              4: f"#SBATCH -t {time}                       # time (HH:MM:SS)\n",
              5: f'#SBATCH --output="{filename_stout}"         # standard output\n',
              6: f'#SBATCH --error="{filename_sterr}"          # standard error\n',
              8: f"#SBATCH -p {partition}\n",
              10: f"input='{filename_g16}'\n",
              11: f'log_path="{log_path}"\n',
            }
    output = []
    for i,line in enumerate(template):
        if i in lines:
            if i == 11 and log_path == None:
                continue
            output.append(lines[i])
        else:
            output.append(line)

    with open(f"{fname}.slurm", "w") as n:
        n.writelines(output)

def create_arkane_input(name, freq_log, pcm_log=None, linear=False, spinMultiplicity=1, opticalIsomers=1, kwargs_lot={}):
    """
    Create an Arkane thermochemistry calculation input file for a Gaussian .log files (must have a frequency calculation within one of the .log files), input as a list. The necessary files will be generated in the same directory in which the function is run, and that directory can be opened in a terminal, in which the RMG-Py environment can be loaded, and Arkane.py can be run on the file named "input.py".

    The "linear" parameter is by default False, and should be set to True if the molecule has D∞h or C∞v symmetry. The symmetry number of the molecule is taken from the frequency calculation. The "opticalIsomers" parameter defaults to 1, and should be changed if chirality is present. Finally, "spinMultiplicity" is also assumed to be 1, and should be changed if necessary to the appropriate spin state.

    Implicit solvation and empirical dispersion are not yet considered by Arkane. Please place a file in the same directory that the function is run, called "input.py" containing the "LevelOfTheory", "atomEnergies", and "frequencyScaleFactor" parameters, which can be obtained from CCCBDB. See "arkaneInputTemplate.py" for an example at the B3LYP/aug-cc-pVDZ level of theory.

    Parameters
    ----------
    name : str
        A str specifying the name of the "molecule" or "species" submitted to Arkane.
    freq_log : str
        A str specifying the relative path of the frequency calculation file for which thermochemistry from Arkane is necessary. This file should be in the same directory as the function is run.
    pcm_log : str
        A str specifying the relative path of the PCM calculation file from which energies are to be used for the Arkane calculation. Optional, defaults to None. This file should be in the same directory as the function is run.
    linear : bool
        A boolean specifying whether molecule is linear. Defaults to False.
    spinMultiplicity : int, Optional, default=1
        A (positive) integer representing the spin state of the system. Defaults to 1, meaning all electrons are spin paired within the system.
    opticalIsomers : int, Optional, default=1
        An integer representing the number of optical isomers the molecule has. Defaults to 1, meaning no chirality.
    kwargs_lot : dict, Optional, default={}
        Keyword arguements for the level of theory specifications in Arkane. See ``write_arkane_input_header`` for options.

    Returns
    ------
    There is no output after correct usage of the function. The generated Arkane input files will appear in the directory within which this function is run.
    """
    with open(freq_log, "r") as f:
        lines = f.readlines()
    symm = 0
    for num, line in enumerate(lines):
        if "Rotational symmetry number" in line:
            symm = line.split()[3]
            symm = int(symm[: symm.find(".")])
    if pcm_log is None:
        with open(f"{name}.py", "w") as s:
            s.writelines(
                [
                    f"linear = {linear}\n\n",
                    f"externalSymmetry = {symm}\n\n",
                    f"spinMultiplicity = {spinMultiplicity}\n\n",
                    f"opticalIsomers = {opticalIsomers}\n\n",
                    f"energy = Log('{freq_log}')\n\n",
                    f"geometry = Log('{freq_log}')\n\n",
                    f"frequencies = Log('{freq_log}')\n\n",
                ]
            )
    elif pcm_log is not None:
        with open(f"{name}.py", "w") as s:
            s.writelines(
                [
                    f"linear = {linear}\n\n",
                    f"externalSymmetry = {symm}\n\n",
                    f"spinMultiplicity = {spinMultiplicity}\n\n",
                    f"opticalIsomers = {opticalIsomers}\n\n",
                    f"energy = Log('{pcm_log}')\n\n",
                    f"geometry = Log('{freq_log}')\n\n",
                    f"frequencies = Log('{freq_log}')\n\n",
                ]
            )

    if os.path.exists("input.py"):
        topOfFile = True
        with open("input.py", "r") as i:
            lines = i.readlines()
        for line in lines:
            if "LevelOfTheory" in line or "atomEnergies" in line or "frequencyScaleFactor" in line:
                topOfFile = False

        if topOfFile:
            write_arkane_input_header("input.py", **kwargs_lot)

    else:
        with open("input.py", "w") as i:
            write_arkane_input_header("input.py", **kwargs_lot)

    with open("input.py", "a") as i:
        i.writelines(
            ["\n\n", f"species('{name}', '{name}.py')\n", f"thermo('{name}', 'NASA')\n\n"]
        )

def write_arkane_input_header(filename, method=None, basis=None):
    """
    Write header for Arkane input.py file.

    If no method or basis set option is given, empty functions are provided for the user to populate.
    The atom energies and frequency scale factor for supported levels of theory can be added

    If the desired atom energies or frequency scaling factor isn't included as expected/desired, feel free to contribute!

    Parameters
    ----------
    filename : str
        The filname of the Arkane input file to write a header to, typically "input.py".
    method : str, Optional, default=None
        Method used in Arkane.LevelOfTheory. This value is also used in the first portion of the atom energies filename
    basis : str, Optional, default=None
        Basis set used in Arkane.LevelOfTheory. This value is also used in the second portion of the atom energies filename

    """

    if method == None:
        flag = False
        method = "ProvideMethodHere"
    else:
        flag = True
    if basis == None:
        flag = False
        basis = "ProvideBasisHere"

    lines = []
    lines.append("LevelOfTheory(method='{}',basis='{}')\n\n".format(method,basis))
    lines.append("atomEnergies = {\n")

    if flag:
        data = json.loads(pkgutil.get_data(__name__, "atom_energies/{}_{}.json".format(method,basis)))
        if "frequencyScaleFactor" in data:
            freq_scaler = data["frequencyScaleFactor"]
        else:
            freq_scaler = None
        if "atomEnergies" in data:
            for atm, eng in data["atomEnergies"].items():
                lines.append("    '{}': {},\n".format(atm,eng))
        else:
            warnings.warn("Internal atom energies file, {}, does not contain atom energies!".format("atom_energies/{}_{}.json".format(method,basis)))
    else:
        lines.append("    'AtomID': EnergyHere,\n")
        freq_scaler = None

    lines.append("}\n\n")
    if freq_scaler != None:
        lines.append("frequencyScaleFactor = {}\n".format(freq_scaler))
    else:
        lines.append("#frequencyScaleFactor = \n")


    with open("input.py", "w") as i:
        i.writelines(
            lines
        )

def extract_coordinates(fname):
    """
    Retrieve a list of strings, each containing a single line representing an atomic symbol and its corresponding coordinates, either from a .out/.log file or directly from a .xyz coordinates file.

    The function supports .xyz, .log, or .out files. For this particular application, the source of a .xyz file is from MDAnalysis written molecular dynamics frame, and the source of .log/.out files are from Gaussian simulation output. The latter can be used to create new input files from the results of a previous Gaussian simulation.

    Parameters
    ----------
    fname : str
        A string specifying the complete path of the file from which coordinates are to be extracted.

    Returns
    -------
    output : list
        A list of formatted strings writeable to a Gaussian simulation input file (.com)
    output2 : array_like
        A 2-D NumPy array containing the coordinates, of shape (atom_count, 3). Applies only to .out/.log files containing converged calculation output, empty for .xyz files.
    atom_count : int
        An integer representing the number of atoms in the system, for use by other functions
    """

    output = []
    output2 = []
    try:
        with open(fname, "r") as f:
            lines = f.readlines()
    except:
        return rf"Could not locate the file {fname}."
    if ".out" in fname or ".log" in fname:
        for num, line in enumerate(lines):
            if "Optimization complete" in line:
                lines = lines[num:]
                break
        for num, line in enumerate(lines):
            if (
                "Proceeding to internal job" in line
                or "Normal termination of Gaussian" in line
            ):
                lines = lines[:num]
                break
        for num, line in enumerate(lines):
            if "Input orientation" in line:
                lines = lines[num + 5 :]
                break
        for num, line in enumerate(lines):
            if "Distance matrix" in line:
                lines = lines[: num - 1]
                break
        for num, line in enumerate(lines):
            line = line.lstrip()
            line = line[line.find(" ") :].lstrip()
            atom = atomic_num[int(line[: line.find(" ")])]
            temp = line[line.find(" ") :].lstrip()
            lines[num] = temp[temp.find(" ") :].lstrip()
            output.append(" " + atom + " " * (6 - len(atom)) + lines[num])
            floatCoords = lines[num].split()
            output2.append([float(c) for c in floatCoords])
    elif ".xyz" in fname:
        for line in lines:
            if len(line.lstrip()) != len(line) and not line.isspace():
                coord = line.lstrip().split()
                coord = "      ".join(coord)
                output.append(coord + "\n")
                output2.append([float(coord.split()[1]), float(coord.split()[2]), float(coord.split()[3])])
    atom_count = len(output)
    output2 = np.array(output2)
    return output, output2, atom_count


def distances(fname):
    """
    Extract a matrix of the distances between each atom and all others within the system from the Gaussian output file (.log/.out).

    The function takes a Gaussian output file with extension .log or .out, and returns a 2-D distance matrix.

    Parameters
    ----------
    fname : str
        A string specifying the complete path of the .log/.out file from which coordinates are to be extracted.

    Returns
    ------
    dist_df : dataframe
        A Pandas dataframe containing the distances between each atom and all others in the system, in Angstroms.
    matrix : array_like
        A 2-D Numpy array containing the distances between each atom and all others in the system, in Angstroms.
    """
    atom_count = extract_coordinates(fname)[2]
    try:
        with open(fname, "r") as f:
            lines = f.readlines()
    except:
        return rf"Could not locate the file {file}."
    for num, line in enumerate(lines):
        if "Optimization complete" in line:
            lines = lines[num:]
            break
    for num, line in enumerate(lines):
        if (
            "Proceeding to internal job" in line
            or "Normal termination of Gaussian" in line
        ):
            lines = lines[:num]
            break
    for num, line in enumerate(lines):
        if "Distance matrix" in line:
            lines = lines[num:]
            break
    for num, line in enumerate(lines):
        if "Stoichiometry" in line:
            lines = lines[:num]
            break
    lines = lines[2:]
    for num, line in enumerate(lines):
        lines[num] = line.lstrip().rstrip()
    if atom_count > 5:
        num_split = int(atom_count / 5)
        for i in range(num_split):
            append = lines[atom_count + 1 : 2 * atom_count + 1 - ((i + 1) * 5)]
            for num, line in enumerate(append):
                temp = line[line.find(" ") :].lstrip()
                append[num] = temp[temp.find(" ") :].lstrip()
                append[num] = append[num].rstrip()
            for j in range(len(append)):
                lines[j + (i + 1) * 5] = lines[j + (i + 1) * 5] + "   " + append[j]
            lines = lines[:atom_count] + lines[2 * atom_count + 1 - (i + 1) * 5 :]
    atom_list = {}
    lines = [
        "".join(
            map(
                str,
                ["      "]
                + [f"{i}" + " " * (11 - len(str(i))) for i in range(1, atom_count + 1)]
                + ["\n"],
            )
        )
    ] + lines
    for i in range(1, len(lines)):
        num = lines[i][: lines[i].find(" ")]
        temp = lines[i][lines[i].find(" ") :].lstrip()
        dist = temp[temp.find(" ") :].lstrip()
        atom_name = temp[: temp.find(" ")].lstrip()
        lines[i] = num + " " * (6 - len(num)) + dist + "\n"
        atom_list[i] = atom_name

    dist_matrix_1 = [line.split() for line in lines[1:]]
    dist_matrix_2 = np.ndarray((atom_count, atom_count))
    for num, row in enumerate(dist_matrix_1):
        row = [float(x) for x in row[1:]]
        for i in range(len(row), atom_count):
            row.append(float(dist_matrix_1[i][num + 1]))
        dist_matrix_2[num] = row

    matrix = np.array(dist_matrix_2)

    header = list(atom_list.values())
    dist_df = pd.DataFrame(
        dist_matrix_2, columns=header, index=[i for i in range(1, atom_count + 1)]
    )
    dist_df.insert(0, "", header)

    return dist_df, matrix


def dGSolvPCM(fname):
    """
    Extract the free energy of solvation from a continuum solvation calculation.

    Parameters
    ----------
    fname : str
        A string specifying the complete path of the file from which solvation free energies are to be extracted.

    Returns
    -------
    gSolv : float
        A float parameter representing the continuum-solvent based solvation free energy from the .log file
    """
    gSolv = 0
    with open(fname, "r") as p:
        gS = p.readlines()
    for line in gS:
        if "DeltaG (solv)" in line:
            gSolv = np.float(line.split()[4])
    return gSolv


def frequencies(fname):
    """
    Extract list of harmonic frequencies from a Gaussian frequency calculation .log/.out file.

    Parameters
    ----------
    fname : str
        A string specifying the complete path of the .log/.out file from which frequencies are to be extracted.

    Returns
    ------
    freq : list
        A list containing the harmonic frequencies of the system, in cm^(-1)
    """
    try:
        with open(fname, "r") as f:
            lines = f.readlines()
    except:
        return rf"Could not locate the file {fname}."
    for num, line in enumerate(lines):
        if " Link1:  Proceeding to internal job step number  2." in line:
            lines = lines[num:]
            break
    for num, line in enumerate(lines):
        if "Harmonic frequencies (cm**-1)" in line:
            lines = lines[num + 4 :]
            break
    for num, line in enumerate(lines):
        if "Thermochemistry" in line:
            lines = lines[:num]
            break
    freqValues = []
    for line in lines:
        if "Frequencies" in line:
            freqValues.append([float(freq) for freq in line.split()[2:]])
    freq = [value for sub in freqValues for value in sub]
    return freq


def nbo_charges(fname):
    """
    Extract list of partial charges on each atom in the system from the Natural Population Analysis of the NBO 3.1 program built into Gaussian.

    Parameters
    ----------
    file : str
        A string specifying the complete path of the .log/.out file from which charges are to be extracted.

    Returns
    ------
    partial_charges : dict
        A dictionary containing keys that specify the atom (type + index), and corresponding values that represent the partial charge on that atom.
    """

    atom_count = extract_coordinates(fname)[2]
    try:
        with open(fname, "r") as f:
            lines = f.readlines()
    except:
        return rf"Could not locate the file {fname}."
    for num, line in enumerate(lines):
        if "Summary of Natural Population Analysis" in line:
            lines = lines[num + 6 : (num + 6) + atom_count]
            break
    partial_charges = {}
    for line in lines:
        line = line.split()
        partial_charges[line[0] + "_" + line[1]] = np.float(line[2])

    return partial_charges


def multipole_moments(fname, center="coc"):
    """
    This function takes atom coordinates and their charges and writes out the dipole and quadrupole moment.

    Parameters
    ----------
    fname : str
        Gaussian .out/.log file from which NBO charges can be extracted, and multipole moments calculated.
    center : str/int/numpy.ndarray, Optional, default="coc"
        Instructions of how to calculate the origin for the calculation. Note that the dipole moment value could be translated later, but the quadrupole moment cannot, so this decision is important. By default, "coc", the center of charge is used. An integer index value that corresponds to an atom can also be used. Finally, an array of length 3, could define the origin.

    Returns
    -------
    dipole : float
        The dipole moment of the set of atoms in Debye
    quadrupole : float
        The quadrupole moment of the set of atoms in Debye*Angstroms

    """
    coords = extract_coordinates(fname)[1]
    partials = list(nbo_charges(fname).values())

    charges = np.array(partials)
    positions = np.array(coords)

    Natoms = len(charges)
    pos_shape = np.shape(positions)
    if pos_shape[0] != Natoms:
        raise ValueError(
            "The first dimension of 'positions', {}, does not match that of charges, {}.".format(
                len(positions), Natoms
            )
        )
    elif len(pos_shape) != 2:
        raise ValueError("The provided positions array should be two dimensional")
    elif pos_shape[1] != 3:
        raise ValueError(
            "The second dimension of the positions array should be of length 3."
        )

    if center == "coc":
        origin = calc_center(positions, charges)
    elif isinstance(center, int):
        if center < 0 or center > Natoms:
            raise ValueError(
                "If 'center' is an integer, the index, {}, must be less that the number of atoms, {}".format(
                    center, Natoms
                )
            )
        origin = positions[center]
    else:
        try:
            origin = np.array(center, float)
        except:
            raise ValueError(
                "If center is not 'coc' or an index, then it should be an array of length 3. The following was provided: {}".format(
                    center
                )
            )
        if len(origin) != 3:
            raise ValueError("The input, center, should be of length 3.")
    recenteredpos = positions - origin

    conv = 0.2081943  # e*A to Debye
    dipole_moment = np.sum(recenteredpos * charges[:, np.newaxis], axis=0)
    dipole = np.sqrt(np.sum(np.square(dipole_moment))) / conv

    tensor = np.zeros((3, 3))
    for i, atom in enumerate(recenteredpos):
        tensor += np.matmul(atom[:, np.newaxis], atom[np.newaxis, :]) * charges[i]

    quad_trace = np.sum(np.diag(tensor))
    tensor = 3 * tensor / 2
    for j in (0, 1, 2):
        tensor[j][j] += -quad_trace / 2
    quad_moment = np.sqrt(2 * np.tensordot(tensor, tensor) / 3)
    quadrupole = quad_moment / conv

    return dipole, quadrupole


def calc_center(positions, weights):
    """
    Calculate the center of a group of coordinates based on some weighting. If the weights are masses, the result is the center of mass, if charges, the center of charge.

    Parameters
    ----------
    positions : numpy.ndarray
        Array of atoms and their coordinates
    weights : numpy.ndarray
        An array used to weight the coordinates

    Returns
    -------
    center : numpy.ndarray
        Coordinates of the center according to the provided weighting

    """
    shape1 = np.shape(np.array(positions))
    shape2 = np.shape(np.array(weights))
    if shape1[0] == shape2:
        raise ValueError(
            "First dimension of coordinate and weighting matrices must be the same"
        )

    weighted_vectors = np.array(positions) * np.array(weights)[:, np.newaxis]
    weight = np.sum(weights)
    center = np.sum(weighted_vectors, axis=0) / weight

    return center

