
#############################################################################################
#initially, we will load everything into hash. 
#name of the chemicals. linked to cid. 
# I dont know if there is a better way to get chemical names to avoid the necessity of this file.
open FILE,"matched-chemicals.txt";
while(<FILE>)
{
	chomp $_;
	@p=split("\t",$_);
	# we trim the chemical name if it is longer than 30 characters. 
	$n=$p[2];
	if(length($n)>30)
	{
		$n=substr($n,0,30);
	}
	$nam{lc($p[0])}=$n;
}
close FILE;


#this file provides the html link and the db of the annotation term.
open FILE,"all-drug-description_ver2.txt";
while(<FILE>)
{
	chomp $_;
	@p=split("\t",$_);
	#indications interfere with the names of side effects. after it is removed, we can delete this.
	if(!($p[1] eq "Indications"))
	{
		# l for html link.
		$l{lc($p[0])}=$p[3];
		# d for description. 
		$d=$p[2];
		# this is only necessary for getting gene names. this doesnt affect other terms. 
		@n=split("\;",$d);
		$d=$n[0];
		# again, we trim the annotation names here.
		if(length($d)>30)
		{
			$d=substr($d,0,30);
		}
		$d{lc($p[0])}=$d;
	}
}
close FILE;


# this is the critical file that you should generate.
open FILE,"enrichment-example2.txt";
while(<FILE>)
{
	chomp $_;
	@p=split("\t",$_);
	$allterms{lc($p[0])}=1;
	$alldrugs{lc($p[1])}=1;
}
close FILE;


open FILE,"example-table.txt";
while(<FILE>)
{
	chomp $_;
	@p=split("\t",$_);
	##############################################################
	# there was an exception and gave error in javascript.
	if($p[2] eq "inf")
	{
		$p[2]=10000;
	}
	if($p[4] eq "inf")
	{
		$p[4]=10000;
	}
	##############################################################
	$pval{lc($p[0])}=$p[2];
	$odds{lc($p[0])}=$p[4];
	# t: annotation type, db.
	$t{lc($p[0])}=$p[1];
}
close FILE;

# here, we create a new file for network visualization.
open NEW,">example-network-ver2.html";

#the first part of the html is copied. 
open FILE,"index1.html";
while(<FILE>)
{
	print NEW $_;
}
close FILE;

#########################################################################################################
# this is the section where the network is created in cytoscape.js readable format. 

foreach $m (keys %allterms)
{
	# so, $m is simply the annotation term. we can use hash to retrieve links, db type, pval and.
	
	$color="#A9A9F5";
	$shape="ellipse";
	#Annotations that I forgot, Chebi, please check again the names and the shape/coloring. a comprehensive example is needed to check this.
	if($t{$m} eq "drug-metabolization")
	{
		#shape is same, only the color should be changed to yellow? 
		$color="#F7FE2E";
		#$shape="triangle";
	}
	if($t{$m} eq "drug-side-effects")
	{
		$color="#F79F81";
		$shape="triangle";
	}
	if($t{$m} eq "drug-Toxicity")
	{
		$color="#F79F81";
		$shape="triangle";
	}
	if($t{$m} eq  "drug-ChEBI-Annotation")
	{
		$color="#D0F5A9";
		$shape="rectangle";
	}
	if($t{$m} eq  "drug-ATC-code")
	{
		$color="#D0F5A9";
		$shape="rectangle";
	}
	if($t{$m} eq "drug-FTC")
	{
		$color="#D0F5A9";
		$shape="rectangle";
	}
	#we need to create node id with annotation-term+db because, one target might be linked to multiple dbs in the case of STITCH, drugbank and metabolization. 
	print NEW "{ data: { id: \'".$m.$t{$m}."\', label: \'".$d{$m}."\', faveColor: \'".$color."\', href:\'".$l{$m}."\', faveShape: \'".$shape."\', weight:30, db: \'".$t{$m}."\', pval: ".(log($pval{$m})/log(10)).", odds: ".$odds{$m}." } },\n";
}

foreach $m (keys %alldrugs)
{
	print NEW "{ data: { id: \'$m\', label: \'".$nam{$m}."\', faveColor: \'#848484\', href:\'http://stitch.embl.de/interactions/".uc($m)."?species=9606\', faveShape: \'".roundrectangle."\', weight:60, db: \'unfiltered\', pval: -10000, odds: 10000 } },\n";
}

print NEW "   ],\n    edges: [\n";

open FILE,"enrichment-example2.txt";
while(<FILE>)
{
	chomp $_;
	@p=split("\t",$_);
	$l1=$p[0];
	$l2=$p[1];
	print NEW "{ data: { source: \'".$l1.$t{$l1}."\', target: \'$l2\' } },\n";
}
close FILE;

#########################################################################################################

#the last part (mainly javascript code) is copied after the table.

open FILE,"index2.html";
while(<FILE>)
{
	print NEW $_;
}
close FILE;

# closing of the visualization html.
close NEW;