# Notice and attribution

ARM-GE contains original ARM64/R36S/PortMaster integration work alongside code derived from earlier open-source and decompilation projects.

Key upstream projects include:

- GoldenEye 007 decompilation/reconstruction: https://github.com/n64decomp/007
- GoldenEye PC/source port: https://github.com/jkdansereau/goldeneye-pc-port
- Perfect Dark PC port / Fast3D lineage: https://github.com/fgsfdsfgs/perfect_dark

The source tree under `work/goldeneye-pc-port/` retains upstream copyright, attribution and license notices. Third-party components retain their own licenses.

The MIT license found in the inherited PC-port tree applies only to the portions identified by that project's notice; it does not automatically relicense decompilation-derived files or third-party code.

## Game data

The public PortMaster package is designed not to contain a GoldenEye ROM or generated ROM-derived sidecar binaries. A compatible ROM must be supplied by the user and required runtime data is generated locally.

Do not add ROM files, bulk extracted game assets, `pcmodels.bin`, `pccg.bin`, or other generated ROM-derived binary data to this repository or release packages.

GoldenEye 007 and associated trademarks belong to their respective rights holders. This project is a non-commercial fan preservation/porting effort and is not affiliated with or endorsed by Nintendo, Rare, MGM, EON Productions, Danjaq, or other rights holders.
