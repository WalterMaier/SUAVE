# hts_motor.py
# 
# Created:  Jan 2014, M. Vegh, 
# Modified: Feb 2014, A. Wendorff
#           Feb 2016, E. Botero     

# ----------------------------------------------------------------------
#   HTS Motor
# ----------------------------------------------------------------------

def hts_motor(max_power):
    """ weight = SUAVE.Methods.Correlations.Propulsion.hts_motor(max_power)
        Calculate the weight of a high temperature superconducting motor
    
        Inputs:
                max_power- maximum power the motor can deliver safely [Watts]
        
        Outputs:
                weight- weight of the motor [kilograms]
            
        Assumptions:
                calculated from fit of commercial available motors
                
                Source: [10] Snyder, C., Berton, J., Brown, G. et all
                'Propulsion Investigation for Zero and Near-Zero Emissions Aircraft,' NASA STI Program,
                NASA Glenn,  2009.012
    """   

    weight = (1./2.2)*2.28*((max_power/1000.)**.6616)  #weight in kg
    
    return weight