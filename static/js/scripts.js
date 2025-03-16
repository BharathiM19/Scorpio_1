document.getElementById("searchPatientForm").addEventListener("submit", function(event) {
    event.preventDefault();
    const patientId = document.getElementById("searchPatientId").value.trim();

    fetch("/search_patient", {
        method: "POST",
        body: new URLSearchParams({ patient_id: patientId }),
        headers: { "Content-Type": "application/x-www-form-urlencoded" }
    })
    .then(response => response.json())
    .then(data => {
        if (data.error) {
            document.getElementById("searchMessage").innerHTML = `<span style="color:red;">${data.error}</span>`;
            document.getElementById("patientSection").classList.add("hidden");
        } else {
            document.getElementById("patientSection").classList.remove("hidden");
            document.getElementById("patientName").textContent = data.patient.name;
            document.getElementById("patientGender").textContent = data.patient.gender;
            document.getElementById("patientDob").textContent = data.patient.dob;
            document.getElementById("patientPhone").textContent = data.patient.phone;
            document.getElementById("patientBloodGroup").textContent = data.patient.blood_group;

            let treatmentHistory = document.getElementById("treatmentHistory");
            treatmentHistory.innerHTML = "";  // Clear previous results

            if (data.treatments.length > 0) {
                data.treatments.forEach(treatment => {
                    let div = document.createElement("div");
                    div.innerHTML = `
                        <strong>Doctor:</strong> ${treatment.doctor_name} <br>
                        <strong>Hospital:</strong> ${treatment.hospital_name} <br>
                        <strong>Operation:</strong> ${treatment.operation_names} <br>
                        <strong>Date:</strong> ${treatment.operation_date} <br>
                        <strong>Description:</strong> ${treatment.description} <hr>
                    `;
                    treatmentHistory.appendChild(div);
                });
            } else {
                treatmentHistory.innerHTML = "<p>No treatment records found.</p>";
            }
        }
    })
    .catch(error => console.error("Error fetching patient data:", error));
});
