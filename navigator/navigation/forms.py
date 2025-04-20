from django import forms

class RouteForm(forms.Form):
    start_lat = forms.DecimalField(label='Start Latitude', max_digits=9, decimal_places=6)
    start_lng = forms.DecimalField(label='Start Longitude', max_digits=9, decimal_places=6)
    end_lat = forms.DecimalField(label='End Latitude', max_digits=9, decimal_places=6)
    end_lng = forms.DecimalField(label='End Longitude', max_digits=9, decimal_places=6)
