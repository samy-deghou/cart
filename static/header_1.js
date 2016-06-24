<!DOCTYPE html>
<!--
European Molecular Biology Laboratory, Heidelberg.
Based an open-source graph theory library written in JavaScript. The library was developed at the Donnelly Centre at the University of Toronto. It is the successor of Cytoscape Web.
Refer to http://js.cytoscape.org/ for details.
--> 
<meta name="robots" content="noindex">
<html>
<head>
<meta name="description" content="CART visualization" />
<link rel="stylesheet" type="text/css" href="http://cart.embl.de/static/cart-res/example.css">

<!-- #dependencies for layout algorithms -->
<script src="http://cart.embl.de/static/cart-res/cola.v3.min.js"></script>
<script src="http://cart.embl.de/static/cart-res/jquery.min.js"></script>

<meta charset=utf-8 />
<title>CART visualization</title>
<!-- main library for network visualization.  -->
  <script src="http://cart.embl.de/static/cart-res/cytoscape.min.js"></script>
  
  
  <!-- START ADDING NEW DEPENDENCIES-->
  <link rel="stylesheet" type="text/css" href="http://cart.embl.de/static/CART-visualization_files/example.css">



<!-- #dependencies for layout algorithms -->







<script type="text/javascript" src="http://cart.embl.de/static/CART-visualization_files/MochiKit/Base.js"></script>

<script type="text/javascript" src="http://cart.embl.de/static/CART-visualization_files/MochiKit/Iter.js"></script>

<script type="text/javascript" src="http://cart.embl.de/static/CART-visualization_files/MochiKit/Logging.js"></script>

<script type="text/javascript" src="http://cart.embl.de/static/CART-visualization_files/MochiKit/DateTime.js"></script>

<script type="text/javascript" src="http://cart.embl.de/static/CART-visualization_files/MochiKit/Format.js"></script>

<script type="text/javascript" src="http://cart.embl.de/static/CART-visualization_files/MochiKit/Async.js"></script>

<script type="text/javascript" src="http://cart.embl.de/static/CART-visualization_files/MochiKit/DOM.js"></script>

<script type="text/javascript" src="http://cart.embl.de/static/CART-visualization_files/MochiKit/Style.js"></script>

<script type="text/javascript" src="http://cart.embl.de/static/CART-visualization_files/MochiKit/LoggingPane.js"></script>

<script type="text/javascript" src="http://cart.embl.de/static/CART-visualization_files/MochiKit/Color.js"></script>

<script type="text/javascript" src="http://cart.embl.de/static/CART-visualization_files/MochiKit/Signal.js"></script>

<script type="text/javascript" src="http://cart.embl.de/static/CART-visualization_files/MochiKit/Style.js"></script>

<script type="text/javascript" src="http://cart.embl.de/static/CART-visualization_files/MochiKit/Position.js"></script>

<script type="text/javascript" src="http://cart.embl.de/static/CART-visualization_files/MochiKit/Visual.js"></script>



<script type="text/javascript" src="http://cart.embl.de/static/CART-visualization_files/SVGKit/SVGKit.js" ></script>

<script type="text/javascript" src="http://cart.embl.de/static/CART-visualization_files/SVGKit/SVGCanvas.js"></script>

<script type="text/javascript" src="http://cart.embl.de/static/CART-visualization_files/FileSaver.js"></script>







<!-- not sure if required. i had problems trying other things. -->



<script src="http://cart.embl.de/static/CART-visualization_files/cola.v3.min.js"></script>



<script src="http://cart.embl.de/static/CART-visualization_files/jquery-2.1.4.min.js"></script>

<script src="http://cart.embl.de/static/CART-visualization_files/cytoscape.js"></script>

  <!-- END ADDING NEW DEPENDENCIES -->
  
  
<style id="jsbin-css">
body { 
  font: 14px helvetica neue, helvetica, arial, sans-serif;
}

</style>
</head>
<body onload="tuck()">

<!-- left panel, network visualization  -->
<div style="width:100%;">
<div style="float:left; width:80%;" id="cy"></div>



<div style="float:right; width:20%;" id="info"> <br>
 <img src="http://cart.embl.de/static/cart-res/cart-labels2.png" width="230" height="90" border="0"><br>
        <br><h2>Database filter</h2>

<!-- images created in illustrator. check ai files in images folder. exported to jpg.  -->
                <!--<img src="http://det.embl.de/~det/img/drugs-logo.png"  width="120" height="45" border="0">--><br>
