"""
Nimi = input("mikä sinun nimesi on?:")
Ikä = input("Kuinka vanha olet?")
puhelin = input("onko sinulla oma puhelin?")
Ikä = float(Ikä)

print(f"terve {Nimi} !")

if Ikä < 18:
    if puhelin == "kyllä":
        print("meille vai teille?")
   elif puhelin == "ei":
        print("Soittele kun on")
else:
    print("Nainen parhaassa iässä!!")


"""
"""

#Kolmion pinta-ala laskuri

Korkeus = float(input("kolmion korkeus:"))
kanta = float(input("kolmion kanta:"))
Pinta_ala = Korkeus * kanta / 2

print(f"pinta-ala on: {Pinta_ala} cm²")

      

"""
"""
#ostoskärryn sisältö:

tuote = input("minkä tuotteen haluat ostaa?:")
hinta = float(input("mikä tuotteen hinta on?:"))
määrä = int(input("kuinka monta kappaletta haluat ostaa?:"))

kok_hinta = hinta * määrä

print(f"olet ostanut {määrä} X {tuote}")
print(f"Loppusummasi on {kok_hinta}€")

"""

"""

adjektiivi1 = input("Kerro jokin adjektiivi:")
objektiivi1 = input("kerro jokin objektiivi:")
sana1 = input("sano jokin sana:")

print(f"Tänään menin {adjektiivi1} eläintarhaan.")
print(f"näin häkissä ison mustan {objektiivi1}")
print(f"Sanoin hänelle että mitäs {sana1} täällä teet?")

"""

"""
Kaverit = 11

#Kaverit += 1
#Kaverit *= 4
#Kaverit = Kaverit ** 2
#Kaverit **= 2
jäljellejää = Kaverit % 3



print(jäljellejää)

"""


"""

#MATIKKAAAA

x = 3.24
y = 4
z = 5

#tulos = round(x)
#Tulos = abs(y) #Kuinka kaukana nollasta luku on
#Tulos = pow(4, 3) #4 potenssiin 3
#Tulos = max(x, y, z) #Maximi arvo
#Tulos = min(x, y, z) #minimi arvo


print(Tulos)

"""
"""
import math

x = 9.9

#print(math.pi)
#print(math.e)

#Tulos = math.sqrt(x) #Neliöjuuri
#Tulos = math.ceil(x) #pyöristää ylöspäin
#Tulos = math.floor(x) #pyöristää alaspäin




print(Tulos)


"""

"""
#ympyrän ympärysmitta laskuri

import math

Halkaisia = float(input("ympyrän halkaisia:"))

r = Halkaisia / 2


P = round(2 * math.pi * r, 2) #mitä pyöristetään ja monenko desimaalin tarkkuudella


print(P)
"""

#ympyrän pinta-ala laskuri

import math

halkaisia = float(input("mikä on ympyrön halkaisia:"))



A = math.pi * pow(halkaisia, 2)


print(f"Ympyrän pinta-ala on: {round(A, 2)}")