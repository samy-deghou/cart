
import java.io.BufferedReader;
import java.io.FileInputStream;
import java.io.IOException;
import java.io.InputStreamReader;

import net.sf.jniinchi.INCHI_RET;

import org.openscience.cdk.DefaultChemObjectBuilder;
import org.openscience.cdk.exception.CDKException;
import org.openscience.cdk.exception.InvalidSmilesException;
import org.openscience.cdk.inchi.InChIGenerator;
import org.openscience.cdk.inchi.InChIGeneratorFactory;
import org.openscience.cdk.interfaces.IAtomContainer;
import org.openscience.cdk.smiles.SmilesParser;

public class Main {
	public static SmilesParser smilesParser = new SmilesParser(DefaultChemObjectBuilder.getInstance());
	public static void main(String[] args) throws InvalidSmilesException, IOException {
		getThing(args[0]);

	}
	public static void getThing(String smiles) throws InvalidSmilesException{
		String toReturn = "";
//		IAtomContainer mol = smilesParser.parseSmiles(smiles);
		try {
                IAtomContainer mol = smilesParser.parseSmiles(smiles);
			InChIGeneratorFactory f = InChIGeneratorFactory.getInstance();
			f.setIgnoreAromaticBonds(true);
			InChIGenerator s = f.getInChIGenerator(mol);
			if (s.getReturnStatus() == INCHI_RET.OKAY) {
				System.out.println(s.getInchiKey());
			} else if (s.getReturnStatus() == INCHI_RET.WARNING) {
				System.out.println(s.getInchiKey());
			};
		} catch (CDKException e) {
			// TODO Auto-generated catch block
			//e.printStackTrace();
			System.out.println("Problem with parsing the SMILE: " + smiles + ":\n" + e);
		}
	}
}
