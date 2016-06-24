   ]
  };

<!-- the network variable is loaded. -->

<!-- ################################################################### -->
<!-- initiation of network visualization -->
 $('#cy').cytoscape({
 	<!-- how much you can zoom in/out. -->
	minZoom: 0.03,
    maxZoom: 300.0,
    motionBlur: true,
    wheelSensitivity:0.05,
	<!-- after checking multiple layouts, this one looks quite good with these parameters. In the next chapter, I will use the same parameters for updating the figure as well.  -->
	layout: {
    name: 'circle',
    animate: true,
    refresh: 8,
    padding: 30,
    randomize           : true,
    nodeRepulsion       : 5000000,
    idealEdgeLength: 50,
    nodeOverlap         : 100,
    edgeElasticity      : 100,
    fit: true,
    initialTemp         :2000,
    numIter: 1000,
  },
  style: cytoscape.stylesheet()
    .selector('node')
      .css({
      	<!-- this helps us to have wider node for drugs in comparison to annotation terms. -->
      	'width': 'mapData(weight, 0, 100,0,100)',
        <!-- node shape. -->
        'shape': 'data(faveShape)',
      	'font-size': 20,
      	'padding-top': '10px',
        'padding-left': '10px',
        'padding-bottom': '10px',
        'padding-right': '10px',
        'text-valign': 'center',
        'content': 'data(label)',
        'background-color': 'data(faveColor)',
      })
    .selector('edge')
      .css({
      	<!-- fixed grey color, subject to change. -->
      	'line-color': '#A4A4A4',
          })
    .selector(':selected')
      .css({
        'line-color': 'black',
        'target-arrow-color': 'black'
      })
    .selector('.faded')
      .css({
      	<!-- this becomes active, if one of the nodes is selected. except its neightbors, all nodes will be shown as faded. -->
        'opacity': 0.3,
        'text-opacity': 0
      }),
     
  <!-- name of the computer-generated enrichment network  -->
  elements: wholenetwork,
  
  ready: function(){
    window.cy = this;
    
    // giddy up...
    <!-- ################################################################################## -->
	<!-- these functions refer to right/left click within the network. -->
    cy.elements().unselectify();
    <!-- right click, link -->
    cy.on('cxttapstart', 'node', function(){
      try { // your browser may block popups
   		 window.open( this.data('href') );
	  } catch(e){ // fall back on url change
   		 window.location.href = this.data('href'); 
  		} 
    });
    <!-- nodes are faded if not neighbors of the selected node.  -->
    cy.on('tap', 'node', function(e){
      var node = e.cyTarget; 
      var neighborhood = node.neighborhood().add(node);
      
      cy.elements().addClass('faded');
      neighborhood.removeClass('faded');
    });
    
    cy.on('tap', function(e){
      if( e.cyTarget === cy ){
        cy.elements().removeClass('faded');
      }
    });
  }
  <!-- ################################################################################## -->
  
     
});


	<!-- this function is for updating the layout with different layout algorithms. For cose and cola, there are additional parameters that were specified with the help of if conditions.  -->
	$("#cy").cy(function(){
		var cy = this;
		
$("#layout-button").bind("click", function(){
			if($("#layout-select").val() == 'cose')
			{
				cy.layout({
				name:  $("#layout-select").val(),
				padding: 30,
			    randomize           : true,
			    animate: true,
			    refresh: 8,
			    nodeRepulsion       : 5000000 * Math.pow(10, $("#repulsion").val()),
			    idealEdgeLength: 50,
			    nodeOverlap         : 100,
			    edgeElasticity      : 100,
			    fit: true,
			    initialTemp         :2000,
			    numIter: 1000});
			}
			if($("#layout-select").val() == 'cola')
			  {
				cy.layout({
				name: $("#layout-select").val(),
				nodeSpacing      : 50 * $("#repulsion").val(),
				padding: 10,
				numIter : 200,
			    randomize : true});
			}
			if($("#layout-select").val() == 'circle')
			  {
				cy.layout({
				name : $("#layout-select").val(),
				radius: 200 * $("#repulsion").val() });
			}
			if($("#layout-select").val() == 'breadthfirst')
			  {
				cy.layout({
				name : $("#layout-select").val(),
				spacingFactor: 1.75 * $("#repulsion").val() });
			}
                        
                        if($("#layout-select").val() == 'grid')
			  {
				cy.layout({
				name : $("#layout-select").val(),
				spacingFactor: 1.75 * $("#repulsion").val() });
			}

                        
			if($("#layout-select").val() == 'concentric')
			  {
				cy.layout({
				name : $("#layout-select").val(),
				minNodeSpacing: 10 * $("#repulsion").val() });
			}
			<!--  the name can be directly used as the name of the layout algorithm  -->
			if(($("#layout-select").val() != 'cose')&&($("#layout-select").val() != 'cola')&&($("#layout-select").val() != 'circle')&&($("#layout-select").val() != 'breadthfirst')&&($("#layout-select").val() != 'concentric'))
			{
			cy.layout({
				name: $("#layout-select").val()
			});
			}
			<!-- after layout, we need to fit to the whole screen. circle is much bigger in comparison to other options, for example.  -->
			cy.fit(cy.$('#j, #e'));
		});	});
	<!-- the sole purpose of this function is to get subset of the network, either baesd on db type or pval,Odds ratio criteria.  -->
	$("#cy").cy(function(){
		$("#redraw-button").bind("click", function(){
			   <!-- In each case, we reinitiate all the network and remove nodes that are unselected.  -->
			   cy.load(wholenetwork);
			   <!-- unchecked boxes will be removed from the network.  -->
			   <!-- Here, the names should match what is specificied from the file. This filtering is only applied to annotation terms while drugs were all retained. In the next step (below), we will remove drugs (nodes) with 0 degree.    -->
			   if(!($("#stitch").is(':checked')))
			   {
			   		 cy.remove("node[db = 'STITCH']"); 
			   }
			   if(!($("#drugbank").is(':checked')))
			   {
			   		 cy.remove("node[db = 'DrugBank']"); 
			   }
			   if(!($("#ttd").is(':checked')))
			   {
			   		 cy.remove("node[db = 'TTD']"); 
			   }
                           if(!($("#ctd").is(':checked')))
			   {
			   		 cy.remove("node[db = 'CTD']"); 
			   }

			   if(!($("#atc").is(':checked')))
			   {
			   		 cy.remove("node[db = 'ATC']"); 
			   }
			   if(!($("#ftc").is(':checked')))
			   {
			   		 cy.remove("node[db = 'ChEMBL-FTC']"); 
			   }

                            if(!($("#sideeffect").is(':checked')))
			   {
			   		 cy.remove("node[db = 'SIDER']"); 
			   }
			   if(!($("#toxicity").is(':checked')))
			   {
			   		 cy.remove("node[db = 'DrugMatrix']"); 
			   }
                           cy.remove("node[[degree < 1]]")
			   <!-- filtering based on pval, there is no magic, here, i try to concatenate strings.  -->
//			   var str1 = "node[pval > ";
//			   var str2 = "]";
//			   var res = str1.concat($("#pval").val() ,str2);
//                           var pval_sam = $("#pval_sam").val()
                           
//                           var res_sam = "node[pval > " + pval_sam + "]"
			   //cy.remove(res);
                           
//                           alert("pval bar : " + res + "\npval sam: " + res_sam)
//                           cy.remove(res_sam)
			   <!--  filtering based on Odds ratio. -->
			   //var str3 = "node[odds < ";
			   //var res2 = str3.concat($("#odds").val() ,str2);
			   //cy.remove(res2);	 
			   <!-- removing all the nodes whose degree is 0.  -->
			   //cy.remove("node[[degree=0]]");
			 	
		});
                $("#filter-pval-button").bind("click",function(){
                    cy.load(wholenetwork);
                    var pval_sam = $("#pval_sam").val()
                    var res_sam = "node[pval > " + pval_sam + "]"
                    cy.remove(res_sam)
                    cy.remove("node[[degree < 1]]")
                });
                
                /// SVG START
                            $("#export").bind("click",function(){
                   //var div= $('#graph_widget' + cy.widgetID), width = div.width(), height = div.height();
                   var svg = new SVGCanvas(2000,1500);
                   
                  SVGCanvas.prototype.setTransform = SVGCanvas.prototype.translate;
				  SVGCanvas.prototype.fillText = SVGCanvas.prototype.text;
				
				 var CanvasRenderer = cytoscape( 'renderer', 'canvas');
				  var orignalUsePaths = CanvasRenderer.usePaths;
				   CanvasRenderer.usePaths = function() { return false; };
  				cy.renderer().renderTo(svg, 0.5, {x: 800, y: 800}, 0.5 );  
  					CanvasRenderer.usePaths = orignalUsePaths;
				
				// Fix rendering issues.
				// Painting order is from bottom to top (logically).
				// All edge lines are painted first. Then all edge strings. Then all nodes, as two circles: one is the contour and the other the filling. Then all node strings.
				// Edges are painted as three consecutive path elements:
				//   1. edge line
				//   2. arrowhead line
				//   3. arrowhead filling
				// .. or just with one line when lacking arrowhead.
				// Paths 2 and 3 are identical except one has stroke and the other fill.

				var children = svg.svg.htmlElement.childNodes;

					var edges = [],
				    remove = [],
				    i = 0;
					// Group the path elements of each edge
					for (; i<children.length; ++i) {
					  var child = children[i];
					  if ('text' === child.localName) break;
					  //switch(child.pathSegList.length) {
                                          switch(2) {
					    case 2:
					      // New graph edge
					      edges.push([child]);
						      break;
						    case 5:
					      // Arrowhead of previous edge
					      edges[edges.length -1].push(child);
					      break;
					  }
					}


					// Fix edge labels: stroke should be white and of 0.2 thickness
					for (; i<children.length; ++i) {
					    var child = children[i];
					    if ('text' !== child.localName) break;
					    child.attributes.stroke.value = '#ffffff';
					    child.style.strokeWidth = '0.2';
					}

					 i = 0;
					// Fix nodes: instead of two separate paths (one for the filling
					// and one for the contour), add a fill value to the contour
					// and delete the other.
					// Also add the text-anchor: middle to the text.
					for (; i<children.length; i+=1) {
					  // The second one is the contour
					  // var child = children[i+1],
					  //  path = child.pathSegList;
					  // The coordinates of the M are wrong:
					  // make the M have the coordinates of the first L
					  // Note: cannot remove the L, circle would draw as semicircle
					  // path[0].x = path[1].x;
					  // path[0].y = path[1].y;
					  // Set the fill value
					  // child.attributes.fill.value = children[i].attributes.fill.value;
					  // Fix text anchor
					  children[i].style.textAnchor = 'middle';
					  // remove.push(children[i]);
					}

					remove.forEach(function(child) {
					  child.parentNode.removeChild(child);
					});

  	              
  	              	var s = new XMLSerializer().serializeToString(svg.svg.htmlElement);

				  var blob = new Blob([s], {type: 'svg'});
				  saveAs(blob, "CART-network.svg");
					
                });
                /// SVG ENDS
                
                $("#filter-odds-button").bind("click", function(){
                    cy.load(wholenetwork);
                    var odds_sam = $("#odds_sam").val()
                    var res_sam = "node[odds < " + odds_sam + "]"
                    cy.remove(res_sam)         
                    cy.remove("node[[degree < 1]]")
                });

	}); 
});
function tuck(){
    var png64 = cy.png();
    $('#network-id').attr('src',png64)
}
</script>
</body>
</html>
