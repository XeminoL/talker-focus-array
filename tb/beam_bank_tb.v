`timescale 1ns / 1ps

module beam_bank_tb;

    parameter CHANNELS = 64;
    parameter TAPS = 64;
    parameter FRAMES = 400;
    parameter FRAME_CYCLES = 7680;
    parameter SHIFT = 20;

    reg clk = 1'b0;
    reg rst = 1'b1;
    reg coef_write = 1'b0;
    reg [11:0] coef_address = 0;
    reg signed [17:0] coef_data = 0;
    reg in_valid = 1'b0;
    reg [5:0] in_channel = 0;
    reg signed [23:0] in_sample = 0;
    wire out_valid;
    wire signed [23:0] out_sample;

    reg [17:0] weights [0:CHANNELS*TAPS-1];
    reg [23:0] stimulus [0:CHANNELS*FRAMES-1];
    integer index;
    integer frame;
    integer channel;
    integer outputs;
    integer file;

    beam_bank dut (
        .clk(clk),
        .rst(rst),
        .coef_write(coef_write),
        .coef_address(coef_address),
        .coef_data(coef_data),
        .shift(SHIFT[5:0]),
        .in_valid(in_valid),
        .in_channel(in_channel),
        .in_sample(in_sample),
        .out_valid(out_valid),
        .out_sample(out_sample)
    );

    always #4 clk = ~clk;

    always @(posedge clk) begin
        if (out_valid) begin
            $fdisplay(file, "%0d", out_sample);
            outputs = outputs + 1;
        end
    end

    initial begin
        $readmemh("beam_weights.hex", weights);
        $readmemh("beam_stimulus.hex", stimulus);
        file = $fopen("beam_rtl.txt", "w");
        outputs = 0;
        repeat (4) @(posedge clk);
        rst <= 1'b0;
        for (index = 0; index < CHANNELS * TAPS; index = index + 1) begin
            @(posedge clk);
            coef_write   <= 1'b1;
            coef_address <= index;
            coef_data    <= weights[index];
        end
        @(posedge clk);
        coef_write <= 1'b0;
        for (frame = 0; frame < FRAMES; frame = frame + 1) begin
            for (channel = 0; channel < CHANNELS; channel = channel + 1) begin
                @(posedge clk);
                in_valid   <= 1'b1;
                in_channel <= channel;
                in_sample  <= stimulus[frame * CHANNELS + channel];
            end
            @(posedge clk);
            in_valid <= 1'b0;
            repeat (FRAME_CYCLES - CHANNELS - 1) @(posedge clk);
        end
        repeat (FRAME_CYCLES) @(posedge clk);
        $fclose(file);
        $display("outputs %0d", outputs);
        $finish;
    end

endmodule
