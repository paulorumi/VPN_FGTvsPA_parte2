# Topologia PNETLab – VPN Fortigate x Palo Alto

## Visão Geral

A topologia utiliza um roteador intermediário (router-internet) simulando a internet entre o Fortigate e o Palo Alto.

```text
LAN-SITE-A (FGT)          LAN-SITE-B (PA)
10.10.10.0/24             10.20.20.0/24
      |                         |
   port2                    ethernet1/2
      |                         |
   Fortigate                 Palo Alto
   port1: 1.1.1.1/30         ethernet1/1: 2.2.2.2/30
        \                     /
         \                   /
          \                 /
          router-internet
          e0/0: 1.1.1.2/30
          e0/1: 2.2.2.1/30