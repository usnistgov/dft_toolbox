%oldchk=sim009_gas.chk
%chk=sim009_PCM.chk
# geom=check rb3lyp-aug-cc-pvdz empiricaldispersion=gd3 int(grid=ultrafine, acc2e=11) scf=(tight,maxcycles=500) scrf=(iefpcm,solvent=water,externaliteration,1stvac,read) nosymm

G16 PCM job for sim009

0 1

dis
cav
rep


