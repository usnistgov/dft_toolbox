%oldchk=sim006_gas.chk
%chk=sim006_PCM.chk
# geom=check rb3lyp-aug-cc-pvdz empiricaldispersion=gd3 int(grid=ultrafine, acc2e=11) scf=(tight,maxcycles=500) scrf=(iefpcm,solvent=water,externaliteration,1stvac,read) nosymm

G16 PCM job for sim006

0 1

dis
cav
rep


