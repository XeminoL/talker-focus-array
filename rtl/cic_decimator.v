`timescale 1ns / 1ps

module cic_decimator #(
    parameter ORDER = 5,
    parameter RATIO = 64,
    parameter WIDTH = 32
) (
    input  wire                    clk,
    input  wire                    rst,
    input  wire                    pdm_valid,
    input  wire                    pdm_bit,
    output reg                     sample_valid,
    output reg  signed [WIDTH-1:0] sample
);

    localparam COUNT_WIDTH = $clog2(RATIO);

    wire signed [WIDTH-1:0] pdm_level = pdm_bit ? 1 : -1;

    reg  signed [WIDTH-1:0] integrator [0:ORDER-1];
    reg  signed [WIDTH-1:0] comb_delay [0:ORDER-1];
    wire signed [WIDTH-1:0] comb_out   [0:ORDER];
    reg  [COUNT_WIDTH-1:0]  phase;

    assign comb_out[0] = integrator[ORDER-1];

    genvar stage;
    generate
        for (stage = 0; stage < ORDER; stage = stage + 1) begin : cic_stage
            wire signed [WIDTH-1:0] integrator_in;

            if (stage == 0) begin : first_stage
                assign integrator_in = pdm_level;
            end else begin : later_stage
                assign integrator_in = integrator[stage-1];
            end

            always @(posedge clk) begin
                if (rst)
                    integrator[stage] <= 0;
                else if (pdm_valid)
                    integrator[stage] <= integrator[stage] + integrator_in;
            end

            assign comb_out[stage+1] = comb_out[stage] - comb_delay[stage];

            always @(posedge clk) begin
                if (rst)
                    comb_delay[stage] <= 0;
                else if (pdm_valid && phase == RATIO - 1)
                    comb_delay[stage] <= comb_out[stage];
            end
        end
    endgenerate

    always @(posedge clk) begin
        if (rst) begin
            phase        <= 0;
            sample_valid <= 1'b0;
            sample       <= 0;
        end else begin
            sample_valid <= 1'b0;
            if (pdm_valid) begin
                phase <= (phase == RATIO - 1) ? 0 : phase + 1'b1;
                if (phase == RATIO - 1) begin
                    sample_valid <= 1'b1;
                    sample       <= comb_out[ORDER];
                end
            end
        end
    end

endmodule
