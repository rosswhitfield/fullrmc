# standard libraries imports
import os

# external libraries imports
import numpy as np

# fullrmc library imports
from fullrmc.Globals import LOGGER, FLOAT_TYPE
from fullrmc.Engine import Engine
from fullrmc.Core.Collection import rebin
from fullrmc.Constraints.CoordinationNumberConstraints import AtomicCoordinationNumberConstraint
from fullrmc.Constraints.PairDistributionConstraints import PairDistributionConstraint
from fullrmc.Constraints.DistanceConstraints import InterMolecularDistanceConstraint
from fullrmc.Constraints.StructureFactorConstraints import ReducedStructureFactorConstraint
from fullrmc.Generators.Swaps import SwapPositionsGenerator

# dirname
DIR_PATH = os.path.dirname( os.path.realpath(__file__) )

# engine file names
engineFileName = "engine.rmc"
grFileName     = "experimental.gr"
sqFileName     = "experimental.fq"
pdbFileName    = "system.pdb" 

# engine variables
grExpPath      = os.path.join(DIR_PATH, grFileName)
sqExpPath      = os.path.join(DIR_PATH, sqFileName)
pdbPath        = os.path.join(DIR_PATH, pdbFileName)
engineFilePath = os.path.join(DIR_PATH, engineFileName)
    
# check Engine already saved
if engineFileName not in os.listdir(DIR_PATH):
    CONSTRUCT = True
else:
    CONSTRUCT = False
  
# set some useful flags
EXPORT_PDB = False  

if CONSTRUCT:    
    # create engine
    ENGINE = Engine(pdb=pdbPath, constraints=None)
    # add G(r) constraint
    PDF_CONSTRAINT = PairDistributionConstraint(engine=None, experimentalData=grExpPath, weighting="atomicNumber")
    ENGINE.add_constraints([PDF_CONSTRAINT]) 
    # add S(Q) constraints
    Sq = np.transpose( rebin(np.loadtxt(sqExpPath) , bin=0.05) ).astype(FLOAT_TYPE)
    RSF_CONSTRAINT = ReducedStructureFactorConstraint(engine=None, experimentalData=Sq, weighting="atomicNumber")
    ENGINE.add_constraints([RSF_CONSTRAINT])
    # add coordination number constraint
    ACN_CONSTRAINT = AtomicCoordinationNumberConstraint(engine=None, thresholdRatio=0.8)
    ENGINE.add_constraints([ACN_CONSTRAINT]) 
    ACN_CONSTRAINT.set_coordination_number_definition( coordNumDef={"ti": [ ('ti',2.5, 3.5, 5, 7), ('ni',2.2, 3.1, 7, 9) ],
                                                                    "ni": [ ('ni',2.5, 3.5, 5, 7), ('ti',2.2, 3.1, 7, 9) ]
                                                                    })
    # add inter-molecular distance constraint
    EMD_CONSTRAINT = InterMolecularDistanceConstraint(engine=None, defaultDistance=2.2)
    ENGINE.add_constraints([EMD_CONSTRAINT]) 
    # save engine
    ENGINE.save(engineFilePath)
else:
    ENGINE = Engine(pdb=None).load(engineFilePath)      


def run_normal(nsteps, saveFrequency, engineFilePath, exportPdb=True):
    ENGINE.set_groups(None)
    ENGINE.run(numberOfSteps=nsteps, saveFrequency=saveFrequency, savePath=engineFilePath)
    if exportPdb:
        ENGINE.export_pdb( os.path.join(DIR_PATH, "pdbFiles","%i.pdb"%(ENGINE.generated)) )

def run_swap(nsteps, saveFrequency, engineFilePath, exportPdb=True):
    #### set swap generators Ni-->Ti and Ti-->Ni ###
    allElements = ENGINE.allElements
    niSwapList = [[idx] for idx in range(len(allElements)) if allElements[idx]=='ni']
    tiSwapList = [[idx] for idx in range(len(allElements)) if allElements[idx]=='ti']
    # create swap generator
    toNiSG = SwapPositionsGenerator(swapList=niSwapList)
    toTiSG = SwapPositionsGenerator(swapList=tiSwapList)
    
    # set swap generator to groups
    for g in ENGINE.groups:
        if allElements[g.indexes[0]]=='ni':
            g.set_move_generator(toTiSG)
        elif allElements[g.indexes[0]]=='ti':
            g.set_move_generator(toNiSG)
    # run
    ENGINE.run(numberOfSteps=nsteps, saveFrequency=saveFrequency, savePath=engineFilePath)
    if exportPdb:
        ENGINE.export_pdb( os.path.join(DIR_PATH, "pdbFiles","%i.pdb"%(ENGINE.generated)) )


# tweak constraints before fitting
PDF_CONSTRAINT, RSF_CONSTRAINT, ACN_CONSTRAINT, EMD_CONSTRAINT = ENGINE.constraints
ACN_CONSTRAINT.set_used(False)    

# export first pdb
if EXPORT_PDB:
    ENGINE.export_pdb( os.path.join("pdbFiles","%i.pdb"%(ENGINE.generated)) )
# run engine
for _ in range(10):
    run_normal(nsteps=100, saveFrequency=100, engineFilePath=engineFilePath, exportPdb=EXPORT_PDB)
for _ in range(99):
    run_normal(nsteps=1000, saveFrequency=1000, engineFilePath=engineFilePath, exportPdb=EXPORT_PDB)
# start fitting scale factors each 10 accepted moves
PDF_CONSTRAINT.set_adjust_scale_factor((10, 0.8, 1.2)) 
RSF_CONSTRAINT.set_adjust_scale_factor((10, 0.8, 1.2)) 
for _ in range(100):
    run_normal(nsteps=9000, saveFrequency=9000, engineFilePath=engineFilePath, exportPdb=EXPORT_PDB)
for _ in range(100):
    run_swap(nsteps=1000, saveFrequency=1000, engineFilePath=engineFilePath, exportPdb=EXPORT_PDB)


