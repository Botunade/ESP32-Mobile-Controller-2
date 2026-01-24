#ifndef PID_H
#define PID_H

#include <Arduino.h>

class PIDController {
public:
    PIDController(float kp, float ki, float kd) 
        : kp(kp), ki(ki), kd(kd), integral(0), prevError(0) {}

    float compute(float setpoint, float measured, float dtSeconds) {
        float error = setpoint - measured;
        
        // Proportional term
        float P = kp * error;

        // Integral term
        integral += error * dtSeconds;
        float I = ki * integral;

        // Derivative term
        float derivative = (error - prevError) / dtSeconds;
        float D = kd * derivative;

        prevError = error;

        // Output = P + I + D
        return P + I + D;
    }

    void reset() {
        integral = 0;
        prevError = 0;
    }

    void setTunings(float kp, float ki, float kd) {
        this->kp = kp;
        this->ki = ki;
        this->kd = kd;
    }

private:
    float kp;
    float ki;
    float kd;
    float integral;
    float prevError;
};

#endif // PID_H
