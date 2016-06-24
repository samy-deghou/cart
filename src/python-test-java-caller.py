import subprocess
import re

smile = "C1CN(CC1NC2=CC=CC3=C2C=CN=C3)CC4=C(C=C(C=C4)Cl)[N+](=O)[O-]"

p1 = subprocess.Popen(["java","-cp" ,".:cdk-1.5.11.jar","Main", smile], stdout=subprocess.PIPE)
output_java_program = p1.stdout.read()
complete_smile = re.split("\n",output_java_program)[-2]
essential_smile = re.split("-",complete_smile)[0]
print essential_smile
