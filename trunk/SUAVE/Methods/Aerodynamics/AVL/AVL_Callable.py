# AVL_Callable.py
#
# Created:  Tim Momose, Dec 2014


# ----------------------------------------------------------------------
#  Imports
# ----------------------------------------------------------------------

import os

# SUAVE imports
from SUAVE.Structure import Data
import SUAVE.Plugins.VyPy.tools.redirect as redirect

# local imports
from .purge_files      import purge_files
from .Data.Results  import Results
from .Data.Settings import Settings


# ----------------------------------------------------------------------
#  Class
# ----------------------------------------------------------------------

class AVL_Callable(Data):
    """ SUAVE.Methods.Aerodynamics.AVL.AVL_Callable
        aerodynamic model that performs a vortex lattice analysis using AVL
        (Athena Vortex Lattice, by Mark Drela of MIT).

        this class is callable, see self.__call__

    """

    def __defaults__(self):
        self.tag        = 'avl'
        self.keep_files = True

        self.settings = Settings()

        self.analysis_temps = Data()
        self.analysis_temps.current_batch_index = 0
        self.analysis_temps.current_batch_file  = None
        self.analysis_temps.current_cases       = None


    def initialize(self,vehicle):

        self.features = vehicle
        self.tag      = 'avl_analysis_of_{}'.format(vehicle.tag)
        self.settings.filenames.run_folder = \
            os.path.abspath(self.settings.filenames.run_folder)
        if not os.path.exists(self.settings.filenames.run_folder):
            os.mkdir(self.settings.filenames.run_folder)

        return

    def translate_results_to_conditions(self,cases,results):
        """ Takes avl results structure containing the results of each run case stored
        	each in its own Data() object. Translates into the Conditions() data structure.
        """
        # set up Conditions structure
        res = Data()
        res.freestream   = Data()
        res.weights      = Data()
        res.aerodynamics = Data()

        res.freestream.velocity    = []
        res.freestream.mach_number = []
        res.freestream.gravity     = []
        res.freestream.density     = []

        res.weights.total_mass     = []
        
        res.aerodynamics.angle_of_attack          = []
        res.aerodynamics.side_slip_angle          = []
        res.aerodynamics.roll_moment_coefficient  = []
        res.aerodynamics.pitch_moment_coefficient = []
        res.aerodynamics.yaw_moment_coefficient   = []
        res.aerodynamics.lift_coefficient         = []
        res.aerodynamics.drag_coefficient         = []
        res.aerodynamics.drag_breakdown           = Data()
        res.aerodynamics.drag_breakdown.induced   = Data()
        res.aerodynamics.drag_breakdown.induced.total = []
        res.aerodynamics.drag_breakdown.induced.efficiency_factor = []
        res.aerodynamics.cz_alpha                 = []
        res.aerodynamics.cy_alpha                 = []
        res.aerodynamics.cl_alpha                 = []
        res.aerodynamics.cm_alpha                 = []
        res.aerodynamics.cn_alpha                 = []
        res.aerodynamics.cz_beta                  = []
        res.aerodynamics.cy_beta                  = []
        res.aerodynamics.cl_beta                  = []
        res.aerodynamics.cm_beta                  = []
        res.aerodynamics.cn_beta                  = []
        res.aerodynamics.neutral_point            = []

        # Move results data to the Conditions data structure
        for i,case_res in enumerate(results):
            res.freestream.velocity.append(cases[i].conditions.freestream.velocity)
            res.freestream.mach_number.append(cases[i].conditions.freestream.mach)
            res.freestream.gravity.append(cases[i].conditions.freestream.gravitational_acceleration)
            res.freestream.density.append(cases[i].conditions.freestream.density)
            res.aerodynamics.angle_of_attack.append(cases[i].conditions.aerodynamics.angle_of_attack)
            res.aerodynamics.side_slip_angle.append(cases[i].conditions.aerodynamics.side_slip_angle)

            res.weights.total_mass.append(cases[i].mass)

            res.aerodynamics.roll_moment_coefficient.append(case_res.aerodynamics.roll_moment_coefficient)
            res.aerodynamics.pitch_moment_coefficient.append(case_res.aerodynamics.pitch_moment_coefficient)
            res.aerodynamics.yaw_moment_coefficient.append(case_res.aerodynamics.yaw_moment_coefficient)
            res.aerodynamics.lift_coefficient.append(case_res.aerodynamics.total_lift_coefficient)
            res.aerodynamics.drag_coefficient.append(case_res.aerodynamics.total_drag_coefficient)
            res.aerodynamics.drag_breakdown.induced.total.append(case_res.aerodynamics.induced_drag_coefficient)
            res.aerodynamics.drag_breakdown.induced.efficiency_factor.append(case_res.aerodynamics.span_efficiency_factor)
            res.aerodynamics.cz_alpha.append(-case_res.stability.alpha_derivatives.lift_curve_slope)
            res.aerodynamics.cy_alpha.append(case_res.stability.alpha_derivatives.side_force_derivative)
            res.aerodynamics.cl_alpha.append(case_res.stability.alpha_derivatives.roll_moment_derivative)
            res.aerodynamics.cm_alpha.append(case_res.stability.alpha_derivatives.pitch_moment_derivative)
            res.aerodynamics.cn_alpha.append(case_res.stability.alpha_derivatives.yaw_moment_derivative)
            res.aerodynamics.cz_beta.append(-case_res.stability.beta_derivatives.lift_coefficient_derivative)
            res.aerodynamics.cy_beta.append(case_res.stability.beta_derivatives.side_force_derivative)
            res.aerodynamics.cl_beta.append(case_res.stability.beta_derivatives.roll_moment_derivative)
            res.aerodynamics.cm_beta.append(case_res.stability.beta_derivatives.pitch_moment_derivative)
            res.aerodynamics.cn_beta.append(case_res.stability.beta_derivatives.yaw_moment_derivative)
            res.aerodynamics.neutral_point.append(case_res.stability.neutral_point)

        return res


    def __call__(self,cases):
        """ process vehicle to setup geometry, condititon and configuration

            Inputs:
                conditions - DataDict() of aerodynamic conditions

            Outputs:
                CL - array of lift coefficients, same size as alpha
                CD - array of drag coefficients, same size as alpha

            Assumptions:
                linear intperolation surrogate model on Mach, Angle of Attack
                    and Reynolds number
                locations outside the surrogate's table are held to nearest data
                no changes to initial geometry or configuration

        """
        assert cases is not None and len(cases) , 'run_case container is empty or None'

        self.analysis_temps.current_cases = cases
        self.analysis_temps.current_batch_index  += 1
        self.analysis_temps.current_batch_file = self.settings.filenames.batch_template.format(self.analysis_temps.current_batch_index)

        for case in cases:
            case.result_filename = self.settings.filenames.output_template.format(self.analysis_temps.current_batch_index,case.index)

        with redirect.folder(self.settings.filenames.run_folder,[],[],False):
            write_geometry(self)
            write_run_cases(self)
            write_input_deck(self)

            results_avl = run_analysis(self)

        results = self.translate_results_to_conditions(cases,results_avl)

        if not self.keep_files:
            from shutil import rmtree
            rmtree(os.path.abspath(self.settings.filenames.run_folder))

        return results





##############################
## Methods used in __call__ ##
##############################

def write_geometry(self):
    # imports
    from .write_geometry import make_header_text,translate_avl_wing,make_surface_text,translate_avl_body,make_body_text

    # unpack inputs
    aircraft      = self.features
    geometry_file = self.settings.filenames.features

    # Open the geometry file after purging if it already exists
    purge_files([geometry_file])

    with open(geometry_file,'w') as geometry:

        header_text = make_header_text(self)
        geometry.write(header_text)
        for w in aircraft.wings:
            avl_wing = translate_avl_wing(w)
            wing_text = make_surface_text(avl_wing)
            geometry.write(wing_text)
        for b in aircraft.fuselages:
            avl_body = translate_avl_body(b)
            body_text = make_body_text(avl_body)
            geometry.write(body_text)

    return


def write_run_cases(self):

    # imports
    from .write_run_cases import make_controls_case_text

    # unpack avl_inputs
    batch_filename = self.analysis_temps.current_batch_file
    aircraft       = self.features

    base_case_text = \
'''

 ---------------------------------------------
 Run case  {0}:   {1}

 alpha        ->  alpha       =   {2}
 beta         ->  beta        =   {3}
 pb/2V        ->  pb/2V       =   0.00000
 qc/2V        ->  qc/2V       =   0.00000
 rb/2V        ->  rb/2V       =   0.00000
{4}

 alpha     =   0.00000     deg
 beta      =   0.00000     deg
 pb/2V     =   0.00000
 qc/2V     =   0.00000
 rb/2V     =   0.00000
 CL        =   0.00000
 CDo       =   {5}
 bank      =   0.00000     deg
 elevation =   0.00000     deg
 heading   =   0.00000     deg
 Mach      =   {6}
 velocity  =   {7}     m/s
 density   =   {8}     kg/m^3
 grav.acc. =   {9}     m/s^2
 turn_rad. =   0.00000     m
 load_fac. =   0.00000
 X_cg      =   {10}     m
 Y_cg      =   {11}     m
 Z_cg      =   {12}     m
 mass      =   {13}     kg
 Ixx       =   {14}     kg-m^2
 Iyy       =   {15}     kg-m^2
 Izz       =   {16}     kg-m^2
 Ixy       =   {17}     kg-m^2
 Iyz       =   {18}     kg-m^2
 Izx       =   {19}     kg-m^2
 visc CL_a =   0.00000
 visc CL_u =   0.00000
 visc CM_a =   0.00000
 visc CM_u =   0.00000

'''#{4} is a set of control surface inputs that will vary depending on the control surface configuration


    # Open the geometry file after purging if it already exists
    purge_files([batch_filename])
    with open(batch_filename,'w') as runcases:

        x_cg = self.features.mass_properties.center_of_gravity[0]
        y_cg = self.features.mass_properties.center_of_gravity[1]
        z_cg = self.features.mass_properties.center_of_gravity[2]
        mass = 0 #self.default_case.mass TODO: FIGURE OUT WHAT TO DEFAULT MASS TO, AND WHERE TO STORE IT BEFORE ANALYSIS.
        moments_of_inertia = aircraft.mass_properties.moments_of_inertia.tensor
        Ixx  = moments_of_inertia[0][0]
        Iyy  = moments_of_inertia[1][1]
        Izz  = moments_of_inertia[2][2]
        Ixy  = moments_of_inertia[0][1]
        Iyz  = moments_of_inertia[1][2]
        Izx  = moments_of_inertia[2][0]

        for case in self.analysis_temps.current_cases:
            index = case.index
            name  = case.tag
            alpha = case.conditions.aerodynamics.angle_of_attack
            beta  = case.conditions.aerodynamics.side_slip_angle
            CD0   = case.conditions.aerodynamics.parasite_drag
            mach  = case.conditions.freestream.mach
            v     = case.conditions.freestream.velocity
            rho   = case.conditions.freestream.density
            g     = case.conditions.freestream.gravitational_acceleration

            # form controls text
            controls = []
            for cs in case.stability_and_control.control_deflections:
                cs_text = make_controls_case_text(cs)
                controls.append(cs_text)
            controls_text = ''.join(controls)
            case_text = base_case_text.format(index,name,alpha,beta,controls_text,
                                              CD0,mach,v,rho,g,x_cg,y_cg,z_cg,mass,
                                              Ixx,Iyy,Izz,Ixy,Iyz,Izx)
            runcases.write(case_text)

    return


def write_input_deck(self):

    base_input = \
'''OPER
'''
    # unpack
    files_path        = self.settings.filenames.run_folder
    deck_filename     = self.settings.filenames.input_deck

    # purge old versions and write the new input deck
    purge_files([deck_filename])
    with open(deck_filename,'w') as input_deck:

        input_deck.write(base_input)
        for case in self.analysis_temps.current_cases:
            case_command = make_case_command(self,case)
            input_deck.write(case_command)
        input_deck.write('\n\nQUIT\n')

    return


def make_case_command(self,case):

    base_case_command = \
'''{0}
x
{1}
{2}
'''
    directory = self.settings.filenames.run_folder
    index = case.index
    case_tag = case.tag
    res_type = 'st' # This needs to change to multiple ouputs if you want to add the ability to read other types of results
    results_file = case.result_filename
    purge_files([results_file],directory)
    case_command = base_case_command.format(index,res_type,results_file)

    return case_command


def run_analysis(self):

    avl_bin_path      = self.settings.filenames.avl_bin_name
    files_path        = self.settings.filenames.run_folder
    geometry_filename = self.settings.filenames.features
    deck_filename     = self.settings.filenames.input_deck

    call_avl(self)

    results = read_results(self)

    return results


def call_avl(self):

    import sys
    import time
    import subprocess
    import SUAVE.Plugins.VyPy.tools.redirect as redirect

    log_file = self.settings.filenames.log_filename
    err_file = self.settings.filenames.err_filename
    purge_files([log_file,err_file])
    avl_call = self.settings.filenames.avl_bin_name
    geometry = self.settings.filenames.features
    in_deck  = self.settings.filenames.input_deck
    batch    = self.analysis_temps.current_batch_file

    with redirect.output(log_file,err_file):

        ctime = time.ctime() # Current date and time stamp
        sys.stdout.write("Log File of System stdout from AVL Run \n{}\n\n".format(ctime))
        sys.stderr.write("Log File of System stderr from AVL Run \n{}\n\n".format(ctime))

        with open(in_deck,'r') as commands:
            avl_run = subprocess.Popen([avl_call,geometry,batch],stdout=sys.stdout,stderr=sys.stderr,stdin=subprocess.PIPE)
            for line in commands:
                avl_run.stdin.write(line)
        avl_run.wait()

        exit_status = avl_run.returncode
        ctime = time.ctime()
        sys.stdout.write("\nProcess finished: {0}\nExit status: {1}\n".format(ctime,exit_status))
        sys.stderr.write("\nProcess finished: {0}\nExit status: {1}\n".format(ctime,exit_status))        

    return exit_status


def read_results(self):

    results = Data()

    for case in self.analysis_temps.current_cases:
        res_file = open(case.result_filename)
        num_ctrl = len(case.stability_and_control.control_deflections)

        try:
            case_res = Results()
            case_res.tag = case.result_filename
            lines   = res_file.readlines()
            case_res.aerodynamics.roll_moment_coefficient  = float(lines[19][32:42].strip())
            case_res.aerodynamics.pitch_moment_coefficient = float(lines[20][32:42].strip())
            case_res.aerodynamics.yaw_moment_coefficient   = float(lines[21][32:42].strip())
            case_res.aerodynamics.total_lift_coefficient   = float(lines[23][10:20].strip())
            case_res.aerodynamics.total_drag_coefficient   = float(lines[24][10:20].strip())
            case_res.aerodynamics.induced_drag_coefficient = float(lines[25][32:42].strip())
            case_res.aerodynamics.span_efficiency_factor   = float(lines[27][32:42].strip())

            case_res.stability.alpha_derivatives.lift_curve_slope           = float(lines[36+num_ctrl][25:35].strip())
            case_res.stability.alpha_derivatives.side_force_derivative      = float(lines[37+num_ctrl][25:35].strip())
            case_res.stability.alpha_derivatives.roll_moment_derivative     = float(lines[38+num_ctrl][25:35].strip())
            case_res.stability.alpha_derivatives.pitch_moment_derivative    = float(lines[39+num_ctrl][25:35].strip())
            case_res.stability.alpha_derivatives.yaw_moment_derivative      = float(lines[40+num_ctrl][25:35].strip())
            case_res.stability.beta_derivatives.lift_coefficient_derivative = float(lines[36+num_ctrl][44:55].strip())
            case_res.stability.beta_derivatives.side_force_derivative       = float(lines[37+num_ctrl][44:55].strip())
            case_res.stability.beta_derivatives.roll_moment_derivative      = float(lines[38+num_ctrl][44:55].strip())
            case_res.stability.beta_derivatives.pitch_moment_derivative     = float(lines[39+num_ctrl][44:55].strip())
            case_res.stability.beta_derivatives.yaw_moment_derivative       = float(lines[40+num_ctrl][44:55].strip())
            case_res.stability.neutral_point                                = float(lines[50+13*(num_ctrl>0)][22:33].strip())

            results.append(case_res)

        finally:
            res_file.close()

    return results