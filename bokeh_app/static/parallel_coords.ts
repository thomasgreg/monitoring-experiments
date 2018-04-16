import {div, empty} from "core/dom"
import * as p from "core/properties"
import {LayoutDOM, LayoutDOMView} from "models/layouts/layout_dom"


export class ParallelCoordsView extends LayoutDOMView {
    foreground: any
    extents: any

    // todo: fix up and width and height
    get_height() {
        return 10;
    }

    get_width() {
        return 10;
    }

    initialize(options: any): void {
        super.initialize(options)
        // console.log('re-initialising')

        this.extents = {'extents': {}}

        this.render()

        this.connect(this.model.data_source.streaming, () => this.render())
        this.connect(this.model.data_source.change, () => this.set_selection())
    }

    set_selection(){
        let indices: Array = this.model.data_source.selected['1d'].indices
        if (indices.length === 0) {
            this.foreground.style("display", null);
        } else {
            this.foreground.style("display", function (d, i) {
                return (indices.indexOf(i) === -1) ? "none" : null;
            });
        }
    }

    render() {
        // console.log("Re-rendering")
        empty(this.el)
        let model = this.model;

        let margin = {top: 30, right: 10, bottom: 10, left: 10},
            width = 960 - margin.left - margin.right,
            height = 300 - margin.top - margin.bottom;

        let x = d3.scale.ordinal().rangePoints([0, width], 1),
            y = {},
            dragging = {};

        let line = d3.svg.line(),
            axis = d3.svg.axis().orient("left"),
            background;

        let svg = d3.select(this.el).append("svg")
            .attr("width", width + margin.left + margin.right)
            .attr("height", height + margin.top + margin.bottom)
            .append("g")
            .attr("transform", "translate(" + margin.left + "," + margin.top + ")");

        // function to get the data in format for d3js
        let data_d3 = [];
        let row = {};
        let data = model.data_source.data

        for (let i = 0; i < model.data_source.get_length(); i++) {
            row = {};
            for (let k of Object.keys(model.dtypes)) {
                row[k] = data[k][i];
            }
            data_d3.push(row);
        }

        var dtypes = this.model.dtypes;

        var dimensions = [];
        for (let d of d3.keys(data_d3[0])){
            if ((dtypes[d] == 'object') || (dtypes[d] == 'category')) {
                let scale = d3.scale.ordinal().domain(d3.extent(data_d3, function (p) {
                    return p[d];
                }))
                    .rangePoints([height, 0]);
                dimensions.push({
                    name: d,
                    scale: scale,
                    type: 'string'
                });
            } else if (d == 'tstamp') {
                let scale = d3.time.scale().domain(d3.extent(data_d3, function (p) {
                    return +p[d];
                }))
                    .range([height, 0]);
                dimensions.push({
                    name: d,
                    scale: scale,
                    type: 'number', //'datetime',
                })
            } else {
                let scale = d3.scale.linear().domain(d3.extent(data_d3, function (p) {
                    return +p[d];
                }))
                    .range([height, 0]);
                dimensions.push({
                    name: d,
                    scale: scale,
                    type: 'number',
                })
            }
        }

        dimensions.forEach(function(d) {
            y[d.name] = d.scale;
        })

        x.domain(dimensions.map(function(d) { return d.name; }));

        // Add grey background lines for context.
        background = svg.append("g")
            .attr("class", "background")
            .selectAll("path")
            .data(data_d3)
            .enter().append("path")
            .attr("d", path);

        // Add blue foreground lines for focus.
        this.foreground = svg.append("g")
            .attr("class", "foreground")
            .selectAll("path")
            .data(data_d3)
            .enter().append("path")
            .attr("d", path);

        let foreground = this.foreground

        // Add a group element for each dimension.
        let g = svg.selectAll(".dimension")
            .data(dimensions)
            .enter().append("g")
                .attr("class", "dimension")
                .attr("transform", function (d) {
                    return "translate(" + x(d.name) + ")";
                })
            .call(d3.behavior.drag()
                .origin(function (d) {
                    return {x: x(d.name)};
                })
                .on("dragstart", function (d) {
                    dragging[d.name] = x(d.name);
                    background.attr("visibility", "hidden");
                })
                .on("drag", function (d) {
                    dragging[d.name] = Math.min(width, Math.max(0, d3.event.x));
                    foreground.attr("d", path);
                    dimensions.sort(function (a, b) {
                        return position(a) - position(b);
                    });
                    x.domain(dimensions.map(function(d) {return d.name; }));
                    g.attr("transform", function (d) {
                        return "translate(" + position(d) + ")";
                    })
                })
                .on("dragend", function (d) {
                    delete dragging[d.name];
                    transition(d3.select(this)).attr("transform", "translate(" + x(d.name) + ")");
                    transition(foreground).attr("d", path);
                    background
                        .attr("d", path)
                        .transition()
                        .delay(500)
                        .duration(0)
                        .attr("visibility", null);
                }));

        // Add an axis and title.
        g.append("g")
            .attr("class", "axis")
            .each(function (d) {
                d3.select(this).call(axis.scale(y[d.name]));
            })
            .append("text")
            .style("text-anchor", "middle")
            .attr("y", -9)
            .text(function (d) {
                return d.name;
            });

        // Add and store a brush for each axis.
        g.append("g")
            .attr("class", "brush")
            .each(function (d) {
                d3.select(this).call(y[d.name].brush = d3.svg.brush().y(y[d.name]).on(
                    "brushstart", brushstart).on("brush", brush));
            })
            .selectAll("rect")
            .attr("x", -8)
            .attr("width", 16);

        function position(d) {
            let v = dragging[d.name];
            return v == null ? x(d.name) : v;
        }

        function transition(g) {
            return g.transition().duration(500);
        }

        // Returns the path for a given data point.
        function path(d) {
            return line(dimensions.map(function (p) {
                return [position(p), y[p.name](d[p.name])];
            }));
        }

        function brushstart() {
            d3.event.sourceEvent.stopPropagation();
        }

        let this_extents = this.extents;


        for (let d of dimensions){
            if (this_extents['extents'].hasOwnProperty(d.name)){
                y[d.name].brush.extent(this_extents['extents'][d.name]);
            }
        }

        brush(false);

        // Handles a brush event, toggling the display of foreground lines.
        function brush(emit:boolean=true) {
            let actives = dimensions.filter(function (p) {
                    return !y[p.name].brush.empty();
                }),
                extents = actives.map(function (p) {
                    return y[p.name].brush.extent();
                });

            let selected_indices: Array;

            if (actives.length == 0) {
                selected_indices = []
            } else {
                selected_indices = data_d3.map(function (d) {
                    return actives.every(function (p, i) {
                        if (p.type === 'number'){
                            return extents[i][0] <= d[p.name] && d[p.name] <= extents[i][1];
                        }
                        else {
                            return extents[i][0] <= p.scale(d[p.name]) && p.scale(d[p.name]) <= extents[i][1];
                        }
                    });
                }).map(function (v, i) {
                    return v ? i : null;
                }).filter(function (v) {
                    return v != null;
                });
            }
            console.log(`number of selected indices: ${selected_indices.length}`);

            // populate extents
            let ext_new = {}
            actives.forEach(function (p, i) {
                ext_new[p.name] = extents[i];
            });
            this_extents['extents'] = ext_new;

            // if brush is empty for all we deselect all indices
            model.data_source.selected['1d'].indices = selected_indices;

            if (emit) {
                model.data_source.change.emit();
            }
        }
    }
}

export class ParallelCoords extends LayoutDOM {
    // If there is an associated view, this is typically boilerplate.
    default_view = ParallelCoordsView

    // The ``type`` class attribute should generally match exactly the name
    // of the corresponding Python class.
    type = "ParallelCoords"

}

// The @define block adds corresponding "properties" to the JS model. These
// should normally line up 1-1 with the Python model class. Most property
// types have counterparts, e.g. bokeh.core.properties.String will be
// ``p.String`` in the JS implementation. Any time the JS type system is not
// yet as complete, you can use ``p.Any`` as a "wildcard" property type.
ParallelCoords.define({
    data_source: [p.Instance],
    dtypes: [ p.Any, {} ]
})
